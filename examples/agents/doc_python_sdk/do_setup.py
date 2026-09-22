import pathlib
from pydo.aio import Client


async def start_sandbox(do_token, api_key, openai_session_id, environment_id, remote_url=""):
    async with Client(token=do_token) as client:
        response = await client.agents.create_session(
            params={"openai_session_id": openai_session_id},
            body={
                "manifest": pathlib.Path("agent.yaml").read_text(),
                "variables": {
                    "ENV_ID": environment_id,
                    "REMOTE_URL": remote_url,
                    "OPENAI_API_KEY": api_key,
                },
            },
        )
        return response["session"]


async def stop_sandbox(do_token, session_id):
    async with Client(token=do_token) as client:
        await client.agents.destroy_session(session_id=session_id)
