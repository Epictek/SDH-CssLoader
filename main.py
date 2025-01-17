import os, json, asyncio, sys, time
from os import path

from watchdog.events import FileSystemEventHandler
from watchdog.utils import UnsupportedLibc

try:
    from watchdog.observers.inotify import InotifyObserver as Observer
except UnsupportedLibc:
    from watchdog.observers.fsevents import FSEventsObserver as Observer

sys.path.append(os.path.dirname(__file__))

from css_utils import Log, create_dir, create_symlink, Result, get_user_home, get_theme_path, store_read as util_store_read, store_write as util_store_write
from css_inject import Inject
from css_theme import Theme, CSS_LOADER_VER
from css_themepatch import ThemePatch
from css_remoteinstall import install
from css_tab_mapping import get_multiple_tab_mappings, load_tab_mappings, tab_has_element, tab_exists, inject_to_tab

Initialized = False

class FileChangeHandler(FileSystemEventHandler):
    def __init__(self, plugin, loop):
        self.plugin = plugin
        self.loop = loop
        self.last = 0
        self.delay = 5

    def on_modified(self, event):
        Log(f"FS Event: {event}")

        if (not event.src_path.endswith(".css")) or event.is_directory:
            Log("FS Event is not on a CSS file. Ignoring!")
            return

        if ((self.last + self.delay) < time.time() and not self.plugin.busy):
            self.last = time.time()
            Log("Reloading themes due to FS event")
            self.loop.create_task(self.plugin.reset(self.plugin))
        

class Plugin:
    async def dummy_function(self) -> bool:
        return True

    async def fetch_theme_path(self) -> str:
        return get_theme_path()

    async def get_themes(self) -> list:
        return [x.to_dict() for x in self.themes]
    
    async def set_theme_state(self, name : str, state : bool) -> dict:
        Log(f"Setting state for {name} to {state}")
        for x in self.themes:
            if (x.name == name):
                if state:
                    for y in x.dependencies:
                        dependency = await self._get_theme(self, y)
                        if dependency is not None:
                            if dependency.enabled:
                                await dependency.remove()
                            
                            for z in x.dependencies[y]:
                                value = x.dependencies[y][z]
                                for patch in dependency.patches:
                                    if patch.name == z:
                                        patch.set_value(value)
                            
                            await self.set_theme_state(self, dependency.name, True)

                result = await x.inject() if state else await x.remove()
                return result.to_dict()
        
        return Result(False, f"Did not find theme {name}").to_dict()

    async def download_theme_from_url(self, id : str, url : str) -> dict:
        local_themes = [x.name for x in self.themes]
        return (await install(id, url, local_themes)).to_dict()

    async def get_backend_version(self) -> int:
        return CSS_LOADER_VER
    
    async def _get_theme(self, themeName : str) -> Theme | None:
        for x in self.themes:
            if x.name == themeName:
                return x
        
        return None

    async def _get_patch_of_theme(self, themeName : str, patchName : str) -> ThemePatch:
        theme = None
        for x in self.themes:
            if (x.name == themeName):
                theme = x
                break
        
        if theme is None:
            raise Exception(f"Did not find theme '{themeName}'")
        
        themePatch = None
        for x in theme.patches:
            if (x.name == patchName):
                themePatch = x
                break
        
        if themePatch is None:
            raise Exception(f"Did not find patch '{patchName}' for theme '{themeName}'")
        
        return themePatch

    async def set_patch_of_theme(self, themeName : str, patchName : str, value : str) -> dict:
        try:
            themePatch = await self._get_patch_of_theme(self, themeName, patchName)
        except Exception as e:
            return Result(False, str(e))
        
        if (themePatch.value == value):
            return Result(True, "Already injected").to_dict()

        if (value in themePatch.options):
            themePatch.value = value
        
        if (themePatch.theme.enabled):
            await themePatch.remove()
            await themePatch.inject()
        
        await themePatch.theme.save()
        return Result(True).to_dict()
    
    async def set_component_of_theme_patch(self, themeName : str, patchName : str, componentName : str, value : str) -> dict:
        try:
            themePatch = await self._get_patch_of_theme(self, themeName, patchName)
        except Exception as e:
            return Result(False, str(e))

        component = None
        for x in themePatch.components:
            if x.name == componentName:
                component = x
                break
        
        if component == None:
            return Result(False, f"Failed to find component '{componentName}'")
        
        component.value = value
        result = await component.generate_and_reinject()
        if not result.success:
            return result

        await themePatch.theme.save()
        return Result(True).to_dict()
    
    async def reset(self) -> dict:
        self.busy = True
        for x in self.injects:
            await x.remove()

        await self._load(self)
        await self._load_stage_2(self)
        self.busy = False
        return Result(True).to_dict()

    async def delete_theme(self, themeName : str) -> dict:
        theme = None

        for x in self.themes:
            if x.name == themeName:
                theme = x
                break
                
        if (theme == None):
            return Result(False, f"Could not find theme {themeName}").to_dict()
        
        result = await theme.delete()
        if not result.success:
            return result.to_dict()
        
        self.themes.remove(theme)
        await self._cache_lists(self)
        return Result(True).to_dict()

    async def store_read(self, key : str) -> str:
        return util_store_read(key)
    
    async def store_write(self, key : str, val : str) -> dict:
        util_store_write(key, val)
        return Result(True).to_dict()

    async def _inject_test_element(self, tab : str, timeout : int = 3, element_name : str = "test_css_loaded") -> Result:
        attempt = 0
        while True:
            if await self._check_test_element(self, tab, element_name):
                return Result(True)
            else:
                try:
                    await inject_to_tab(tab, 
                    f"""
                    (function() {{
                        const elem = document.createElement('div');
                        elem.id = "{element_name}";
                        document.head.append(elem);
                    }})()
                    """, False)
                except:
                    pass

                attempt += 1

                if (attempt >= timeout):
                    return Result(False, f"Inject into tab '{tab}' was attempted {timeout} times, stopping")

                await asyncio.sleep(1)
            
    
    async def _check_test_element(self, tab : str, element_name : str = "test_css_loaded") -> bool:
        try:
            return await tab_has_element(tab, element_name)
        except:
            return False

    async def _parse_themes(self, themesDir : str, configDir : str = None):
        if (configDir is None):
            configDir = themesDir

        possibleThemeDirs = [str(x) for x in os.listdir(themesDir)]

        for x in possibleThemeDirs:
            themePath = themesDir + "/" + x
            configPath = configDir + "/" + x
            themeDataPath = themePath + "/theme.json"

            if (not path.exists(themeDataPath)) and (not path.exists(os.path.join(themePath, "theme.css"))):
                continue
        
            Log(f"Analyzing theme {x}")
            
            try:
                theme = None
                if path.exists(themeDataPath):
                    with open(themeDataPath, "r") as fp:
                        theme = json.load(fp)
                    
                themeData = Theme(themePath, theme, configPath)

                if (themeData.name not in [x.name for x in self.themes]):
                    self.themes.append(themeData)
                    Log(f"Adding theme {themeData.name}")

            except Exception as e:
                Log(f"Exception while parsing a theme: {e}") # Couldn't properly parse everything

    async def _cache_lists(self):
        self.injects = []
        self.tabs = []

        for x in self.themes:
            injects = x.get_all_injects()
            self.injects.extend(injects)
            for y in injects:
                for z in y.tabs:
                    if z not in self.tabs:
                        self.tabs.append(z)

    async def _check_tabs(self):
        while True:
            await asyncio.sleep(3)
            for x in self.tabs:
                try:
                    if not await tab_exists(x):
                        continue # Tab does not exist, so not worth injecting into it

                    # Log(f"Checking if tab {x} is still injected...")
                    if not await self._check_test_element(self, x):
                        Log(f"Tab {x} is not injected, reloading...")
                        await self._inject_test_element(self, x)
                        for y in self.injects:
                            if y.enabled:
                                (await y.inject(x)).raise_on_failure()
                except Exception as e:
                    Log(f":( {str(e)}")
                    pass

    async def _load(self):
        Log("Loading themes...")
        self.themes = []

        themesPath = f"{get_user_home()}/homebrew/themes"
        defaultThemesPath = f"{get_user_home()}/homebrew/plugins/SDH-CssLoader/themes"

        if (not path.exists(themesPath)):
            create_dir(themesPath)

        await self._parse_themes(self, themesPath)
        if (path.exists(defaultThemesPath)):
            await self._parse_themes(self, defaultThemesPath, themesPath)
    
    async def _set_theme_score(self, theme : Theme):
        if theme.name not in self.scores:
            self.scores[theme.name] = 0
        
        for x in theme.dependencies:
            dependency = await self._get_theme(self, x)
            if dependency is not None:
                await self._set_theme_score(self, dependency)
                self.scores[dependency.name] -= 1

    async def _load_stage_2(self, inject_now : bool = True):
        self.scores = {}
        for x in self.themes:
            await self._set_theme_score(self, x)
        
        Log(self.scores)
        self.themes.sort(key=lambda d: self.scores[d.name])

        for x in self.themes:
            Log(f"Loading theme {x.name}")
            await x.load(inject_now)
        
        await self._cache_lists(self)
        self.themes.sort(key=lambda d: d.name)

    async def _main(self):
        global Initialized
        if Initialized:
            return
        
        Initialized = True

        await asyncio.sleep(1)

        self.busy = False
        self.themes = []
        Log("Initializing css loader...")
        Log(f"Max supported manifest version: {CSS_LOADER_VER}")
        
        await create_symlink(get_theme_path(), f"{get_user_home()}/.local/share/Steam/steamui/themes_custom")
        load_tab_mappings()

        await self._load(self)
        await self._inject_test_element(self, "SP|Steam Big Picture Mode", 9999, "test_ui_loaded")
        await self._load_stage_2(self, False)

        if (os.path.exists(f"{get_theme_path()}/WATCH")):
            Log("Observing themes folder for file changes")
            self.observer = Observer()
            self.handler = FileChangeHandler(self, asyncio.get_running_loop())
            self.observer.schedule(self.handler, get_theme_path(), recursive=True)
            self.observer.start()
        else:
            Log("Not observing themes folder for file changes")

        Log(f"Initialized css loader. Found {len(self.themes)} themes, which inject into {len(self.tabs)} tabs ({self.tabs}). Total {len(self.injects)} injects, {len([x for x in self.injects if x.enabled])} injected")
        await self._check_tabs(self)