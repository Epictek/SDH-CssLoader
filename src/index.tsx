import {
  ButtonItem,
  definePlugin,
  PanelSection,
  PanelSectionRow,
  ServerAPI,
  staticClasses,
  Tabs,
  Router,
} from "decky-frontend-lib";
import { useEffect, useState, FC } from "react";
import * as python from "./python";
import * as api from "./api";
import { RiPaintFill } from "react-icons/ri";

import {
  SettingsPage,
  StarredThemesPage,
  SubmissionsPage,
  ThemeBrowserPage,
  UninstallThemePage,
} from "./theme-manager";
import { CssLoaderContextProvider, CssLoaderState, useCssLoaderState } from "./state";
import { ThemeToggle } from "./components";
import { ExpandedViewPage } from "./theme-manager/ExpandedView";
import { Permissions } from "./apiTypes";

var firstTime: boolean = true;

const Content: FC<{ serverAPI: ServerAPI }> = () => {
  const { localThemeList: themeList } = useCssLoaderState();

  const [dummyFuncResult, setDummyResult] = useState<boolean>(false);

  const reload = function () {
    python.reloadBackend();
    dummyFuncTest();
  };
  function dummyFuncTest() {
    python.resolve(python.dummyFunction(), setDummyResult);
  }

  useEffect(() => {
    dummyFuncTest();
    python.getInstalledThemes();
  }, []);

  return (
    <PanelSection title="Themes">
      {dummyFuncResult ? (
        <>
          <PanelSectionRow>
            <ButtonItem
              layout="below"
              onClick={() => {
                Router.CloseSideMenus();
                Router.Navigate("/theme-manager");
              }}
            >
              Manage Themes
            </ButtonItem>
          </PanelSectionRow>
          {themeList.map((x) => (
            <ThemeToggle data={x} />
          ))}
        </>
      ) : (
        <PanelSectionRow>
          <span>
            CssLoader failed to initialize, try reloading, and if that doesn't work, try restarting
            your deck.
          </span>
        </PanelSectionRow>
      )}

      <PanelSectionRow>
        <ButtonItem layout="below" onClick={() => reload()}>
          Reload Themes
        </ButtonItem>
      </PanelSectionRow>
    </PanelSection>
  );
};

const ThemeManagerRouter: FC = () => {
  const { apiMeData, currentTab, setGlobalState } = useCssLoaderState();
  return (
    <div
      style={{
        marginTop: "40px",
        height: "calc(100% - 40px)",
        background: "#0005",
      }}
    >
      <Tabs
        activeTab={currentTab}
        onShowTab={(tabID: string) => {
          setGlobalState("currentTab", tabID);
        }}
        tabs={[
          {
            title: "All Themes",
            content: <ThemeBrowserPage />,
            id: "ThemeBrowser",
          },
          ...(!!apiMeData
            ? [
                {
                  title: "Starred Themes",
                  content: <StarredThemesPage />,
                  id: "StarredThemes",
                },
                ...(apiMeData.permissions.includes(Permissions.viewSubs)
                  ? [
                      {
                        title: "Submissions",
                        content: <SubmissionsPage />,
                        id: "SubmissionsPage",
                      },
                    ]
                  : []),
              ]
            : []),
          {
            title: "Installed Themes",
            content: <UninstallThemePage />,
            id: "InstalledThemes",
          },
          {
            title: "Settings",
            content: <SettingsPage />,
            id: "SettingsPage",
          },
        ]}
      />
    </div>
  );
};

export default definePlugin((serverApi: ServerAPI) => {
  const state: CssLoaderState = new CssLoaderState();
  python.setServer(serverApi);
  python.setStateClass(state);
  api.setServer(serverApi);
  api.setStateClass(state);

  python.resolve(python.storeRead("shortToken"), (token: string) => {
    if (token) {
      state.setGlobalState("apiShortToken", token);
    }
  });

  serverApi.routerHook.addRoute("/theme-manager", () => (
    <CssLoaderContextProvider cssLoaderStateClass={state}>
      <ThemeManagerRouter />
    </CssLoaderContextProvider>
  ));

  serverApi.routerHook.addRoute("/theme-manager-expanded-view", () => (
    <CssLoaderContextProvider cssLoaderStateClass={state}>
      <ExpandedViewPage />
    </CssLoaderContextProvider>
  ));

  return {
    title: <div className={staticClasses.Title}>CSS Loader</div>,
    alwaysRender: true,
    content: (
      <CssLoaderContextProvider cssLoaderStateClass={state}>
        <Content serverAPI={serverApi} />
      </CssLoaderContextProvider>
    ),
    icon: <RiPaintFill />,
  };
});
