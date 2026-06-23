from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import streamlit as st


@dataclass
class BreezeSessionManager:
    api_key: str = ""
    secret_key: str = ""
    session_token: str = ""
    connected: bool = False
    client: Any | None = None
    error: str | None = None

    @classmethod
    def from_streamlit(cls) -> "BreezeSessionManager":
        api_key = st.secrets.get("BREEZE_API_KEY", os.getenv("BREEZE_API_KEY", ""))
        secret_key = st.secrets.get("BREEZE_SECRET_KEY", os.getenv("BREEZE_SECRET_KEY", ""))
        session_token = st.session_state.get(
            "breeze_session_token",
            st.secrets.get("BREEZE_SESSION_TOKEN", os.getenv("BREEZE_SESSION_TOKEN", "")),
        )
        stored = st.session_state.get("breeze_manager")
        if stored and stored.session_token == session_token:
            return stored
        return cls(api_key=api_key, secret_key=secret_key, session_token=session_token)

    def connect(self, session_token: str | None = None) -> None:
        if session_token is not None:
            self.session_token = session_token.strip()
            st.session_state["breeze_session_token"] = self.session_token

        if not self.api_key or not self.secret_key or not self.session_token:
            self.connected = False
            self.error = "Missing API key, secret key, or session token."
            st.session_state["breeze_manager"] = self
            return

        try:
            from breeze_connect import BreezeConnect

            client = BreezeConnect(api_key=self.api_key)
            client.generate_session(
                api_secret=self.secret_key,
                session_token=self.session_token,
            )
            self.client = client
            self.connected = True
            self.error = None
        except Exception as exc:  # pragma: no cover - depends on Breeze runtime/API.
            self.client = None
            self.connected = False
            self.error = str(exc)

        st.session_state["breeze_manager"] = self

