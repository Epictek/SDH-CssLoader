import { DialogButton, Focusable, PanelSectionRow, TextField } from "decky-frontend-lib";
import { SiWebauthn } from "react-icons/si";
import { useState, VFC } from "react";
import * as python from "../python";
import { useCssLoaderState } from "../state";

export const SettingsPage: VFC = () => {
  const {
    apiUrl,
    apiShortToken,
    apiFullToken,
    setApiShortToken,
    setApiFullToken,
    setApiTokenExpireDate,
    setApiMeData,
    apiMeData,
  } = useCssLoaderState();
  const [shortTokenInterimValue, setShortTokenIntValue] = useState<string>(apiShortToken);

  function authWithShortToken() {
    const shortTokenValue = shortTokenInterimValue;
    if (shortTokenInterimValue.length === 24) {
      python.authWithShortToken(shortTokenValue, apiUrl).then((data) => {
        if (data && data?.token) {
          python.storeWrite("shortToken", shortTokenValue);
          setApiShortToken(shortTokenValue);
          setApiFullToken(data.token);
          setApiTokenExpireDate(new Date().valueOf() + 1000 * 60 * 10);
          python.genericGET(`${apiUrl}/auth/me`, data.token).then((meData) => {
            if (meData?.username) {
              setApiMeData(meData);
            }
          });
        } else {
          python.toast("Error Authenticating", JSON.stringify(data));
        }
      });
    } else {
      python.toast("Invalid Token", "Token must be 24 characters long.");
    }
  }

  return (
    // The outermost div is to push the content down into the visible area
    <div>
      <div>
        <h1 style={{ fontWeight: "bold", fontSize: "2em" }}>
          {apiFullToken ? "Your Account" : "Log In"}
        </h1>
        {apiFullToken ? (
          <>
            <Focusable style={{ display: "flex", alignItems: "center" }}>
              <div style={{ minWidth: "65%", marginRight: "auto" }}>
                {apiMeData ? (
                  <>
                    <span>Logged In As {apiMeData.username}</span>
                  </>
                ) : (
                  <span>Logged In</span>
                )}
              </div>
              <DialogButton
                style={{
                  maxWidth: "30%",
                  height: "50%",
                  marginLeft: "auto",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: "0.5em",
                }}
                onClick={() => {
                  setApiShortToken("");
                  setApiFullToken("");
                  setApiTokenExpireDate(undefined);
                  python.storeWrite("shortToken", "");
                }}
              >
                <span>Unlink My Deck</span>
              </DialogButton>
            </Focusable>
          </>
        ) : (
          <>
            <Focusable style={{ display: "flex", alignItems: "center", width: "100%" }}>
              <div style={{ minWidth: "65%", marginRight: "auto" }}>
                <TextField
                  disabled={!!apiFullToken}
                  label="DeckThemes Account Key"
                  bIsPassword
                  value={shortTokenInterimValue}
                  onChange={(e) => setShortTokenIntValue(e.target.value)}
                />
              </div>
              <DialogButton
                disabled={shortTokenInterimValue.length !== 24}
                onClick={() => {
                  authWithShortToken();
                }}
                style={{
                  maxWidth: "30%",
                  height: "50%",
                  marginLeft: "auto",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: "0.5em",
                }}
              >
                <SiWebauthn style={{ height: "1.5em", width: "1.5em" }} />
                <span>Log In</span>
              </DialogButton>
            </Focusable>
          </>
        )}
      </div>
      <Focusable>
        <div>
          <h1 style={{ fontWeight: "bold", fontSize: "2em" }}>About CSSLoader</h1>
          <h2 style={{ fontWeight: "bold", fontSize: "1.5em", marginBottom: "0px" }}>Developers</h2>
          <ul style={{ marginTop: "0px", marginBottom: "0px" }}>
            <li>
              <span>SuchMeme - github.com/suchmememanyskill</span>
            </li>
            <li>
              <span>EMERALD - github.com/EMERALD0874</span>
            </li>
            <li>
              <span>Beebles - github.com/beebls</span>
            </li>
          </ul>
          <h2 style={{ fontWeight: "bold", fontSize: "1.5em", marginBottom: "0px" }}>Support</h2>
          <span>
            See the DeckThemes Discord server for support.
            <br />
            discord.gg/HsU72Kfnpf
          </span>
          <h2 style={{ fontWeight: "bold", fontSize: "1.5em", marginBottom: "0px" }}>
            Create and Submit Your Own Theme
          </h2>
          <span>
            Instructions for theme creation/submission are available DeckThemes' docs website.
            <br />
            docs.deckthemes.com
          </span>
        </div>
      </Focusable>
    </div>
  );
};
