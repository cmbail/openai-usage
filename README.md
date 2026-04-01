# OpenAI Usage by Project
# By Christian Bailey https://github.com/cmbail

Small Python script that prints OpenAI API usage and cost grouped by project.

It calls the OpenAI organization administration API and aggregates cost buckets by `project_id`.

## Requirements

- Python 3.10+
- uv package manager
- macOS (script reads the API key from Keychain)

## Setup

Clone the repo:
git clone https://github.com/YOURNAME/openai-usage.git
cd openai-usage

Install dependencies:
uv sync

## Store your OpenAI admin key

Save the key to macOS Keychain:
security add-generic-password -s openai_admin_key -w 'YOUR_ADMIN_KEY' -U

The script will retrieve the key from Keychain automatically.

## Run
uv run openai-usage.py

Example output:
OpenAI API cost by project for last 30 days
Project Project ID Cost (USD)
Default proj_xxxxxx 42.12
Squawk AI Release proj_xxxxxx 18.40
Whisper proj_xxxxxx 2.03
TOTAL 62.55

## Security

The API key is **never stored in the repo**.

The script retrieves the key from macOS Keychain using the `security` CLI.

## License

MIT