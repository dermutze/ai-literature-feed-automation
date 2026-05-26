# n8n Node Parameters

This guide shows generic n8n node settings for the AI Literature Research Feed Automation project.

It covers two common setups:

1. **Production Docker Compose stack**
   n8n and the FastAPI service run in the same Docker Compose network.

2. **Existing standalone n8n container**
   n8n is already running separately, and the API runs either locally or in a separate container.

---

## Expected Data Mount

The project writes generated outputs to the local `data/` folder:

```text
data/
├── bibtex/
├── digests/
├── feeds/
└── ris/
```

Inside the n8n container, this folder should be mounted as:

```text
/home/node/.n8n-files
```

This allows n8n to read generated files as email attachments.

---

## Option A — Production Docker Compose Setup

In the production `docker-compose.yml`, mount the project `data/` folder into n8n:

```yaml
services:
  n8n:
    image: n8nio/n8n:latest
    volumes:
      - ${N8N_HOME:-./.n8n}:/home/node/.n8n
      - ./data:/home/node/.n8n-files
```

With this setup, n8n can read:

```text
/home/node/.n8n-files/bibtex/
/home/node/.n8n-files/ris/
/home/node/.n8n-files/digests/
/home/node/.n8n-files/feeds/
```

---

## Option B — Existing Standalone n8n Container

If you already run n8n separately, recreate your n8n container with an extra volume mount for the project output folder.

Generic example:

```bash
docker stop n8n
docker rm n8n

docker run -it -d \
  --literature-n8n \
  -p 5679:5678 \
  -v /path/to/n8n-data:/home/node/.n8n \
  -v /path/to/project/data:/home/node/.n8n-files \
  n8nio/n8n:latest
```

Replace these paths:

```text
/path/to/n8n-data
```

with the folder where your n8n workflows and credentials are stored.

```text
/path/to/project/data
```

with the `data/` folder of this project.

Do not commit your n8n data folder to GitHub.

---

## HTTP Request Node

Use an **HTTP Request** node to trigger the feed.

### Production Compose Network

When n8n and the API are in the same Docker Compose network, use the API service name:

```text
POST http://literature-feed-api:8000/run_feed
```

### Existing n8n Container + API on Host Machine

When n8n is a standalone container and the API runs on the host machine:

```text
POST http://host.docker.internal:8000/run_feed
```

On some Linux or WSL setups, this may be needed instead:

```text
POST http://172.17.0.1:8000/run_feed
```

### API Running Directly on the Same Machine

From a browser or local shell, the API is usually available at:

```text
http://localhost:8000
```

Inside a Dockerized n8n container, do not use `localhost:8000` to reach a host API. Inside the container, `localhost` means the n8n container itself.

---

## HTTP Request Headers

Use:

```json
{
  "Content-Type": "application/json"
}
```

---

## HTTP Request Body

Basic run without LLM summarization:

```json
{
  "use_ollama": false,
  "max_returned_papers": 20
}
```

Run with local Ollama summarization:

```json
{
  "use_ollama": true,
  "max_returned_papers": 10
}
```

You can adjust `max_returned_papers` to control the number of selected papers.

---

## Expected API Output Fields

The API response is expected to include:

```text
raw_count
processed_count
outputs.feed
outputs.digest
outputs.bibtex
outputs.ris
papers
```

Useful n8n expressions:

```text
{{$json.outputs.bibtex}}
{{$json.outputs.ris}}
{{$json.outputs.digest}}
{{$json.outputs.feed}}
{{$json.processed_count}}
{{$json.raw_count}}
```

---

## Recommended Node Name

For the examples below, assume the node holding the API response is named:

```text
Papers selection
```

If your node has another name, replace `Papers selection` with your exact node name.

---

## Reading Generated Files as Attachments

The API may return file paths such as:

```text
/app/data/bibtex/feed_2026-05-26.bib
/workspace/data/bibtex/feed_2026-05-26.bib
data/bibtex/feed_2026-05-26.bib
```

n8n should read files from its own mounted path:

```text
/home/node/.n8n-files
```

Therefore, extract only the filename from the API output and rebuild the container-readable path.

---

## Attachment File Path Expressions

### BibTeX Attachment

```text
=/home/node/.n8n-files/bibtex/{{$('Papers selection').first().json.outputs.bibtex.split('/').pop()}}
```

### RIS Attachment

```text
=/home/node/.n8n-files/ris/{{$('Papers selection').first().json.outputs.ris.split('/').pop()}}
```

### Markdown Digest Attachment

```text
=/home/node/.n8n-files/digests/{{$('Papers selection').first().json.outputs.digest.split('/').pop()}}
```

### JSONL Feed Attachment

```text
=/home/node/.n8n-files/feeds/{{$('Papers selection').first().json.outputs.feed.split('/').pop()}}
```

---

## Read/Write Files from Disk Node

Use one **Read/Write Files from Disk** node per attachment.

Suggested settings:

### BibTeX

```text
Operation: Read File from Disk
File Path: =/home/node/.n8n-files/bibtex/{{$('Papers selection').first().json.outputs.bibtex.split('/').pop()}}
Put Output File in Field: bibtex_attachment
```

### RIS

```text
Operation: Read File from Disk
File Path: =/home/node/.n8n-files/ris/{{$('Papers selection').first().json.outputs.ris.split('/').pop()}}
Put Output File in Field: ris_attachment
```

### Digest

```text
Operation: Read File from Disk
File Path: =/home/node/.n8n-files/digests/{{$('Papers selection').first().json.outputs.digest.split('/').pop()}}
Put Output File in Field: digest_attachment
```

### Feed JSONL

```text
Operation: Read File from Disk
File Path: =/home/node/.n8n-files/feeds/{{$('Papers selection').first().json.outputs.feed.split('/').pop()}}
Put Output File in Field: feed_attachment
```

---

## Email Node Attachment Setup

After reading the files from disk, pass the binary fields to the email node.

Suggested binary property names:

```text
bibtex_attachment
ris_attachment
digest_attachment
feed_attachment
```

Depending on your email node, add these binary fields under the attachment section.

For a simple digest email, attach:

```text
bibtex_attachment
ris_attachment
digest_attachment
```

The JSONL feed is optional.

---

## Example Email Subject

```text
AI Literature Feed Digest
```

Or with the number of selected papers:

```text
=AI Literature Feed Digest - {{$('Papers selection').first().json.processed_count}} papers
```

---

## Example Email Body

```text
Hello,

The latest AI literature feed has been generated.

Raw papers collected:
{{$('Papers selection').first().json.raw_count}}

Papers selected:
{{$('Papers selection').first().json.processed_count}}

Attached:
- Markdown digest
- BibTeX export
- RIS export

Best,
AI Literature Feed Monitor
```

---

## Testing File Visibility inside n8n

### Production Compose Container

```bash
docker exec -it literature-n8n ls -lah /home/node/.n8n-files
docker exec -it literature-n8n ls -lah /home/node/.n8n-files/bibtex
docker exec -it literature-n8n ls -lah /home/node/.n8n-files/ris
docker exec -it literature-n8n ls -lah /home/node/.n8n-files/digests
docker exec -it literature-n8n ls -lah /home/node/.n8n-files/feeds
```

### Existing Standalone n8n Container

```bash
docker exec -it n8n ls -lah /home/node/.n8n-files
docker exec -it n8n ls -lah /home/node/.n8n-files/bibtex
docker exec -it n8n ls -lah /home/node/.n8n-files/ris
docker exec -it n8n ls -lah /home/node/.n8n-files/digests
docker exec -it n8n ls -lah /home/node/.n8n-files/feeds
```

---

## Testing API Access from n8n

If n8n has shell tools available, test:

```bash
docker exec -it literature-n8n wget -qO- http://literature-feed-api:8000/health
```

For a standalone n8n container calling a host API:

```bash
docker exec -it n8n wget -qO- http://host.docker.internal:8000/health
```

If `wget` or `curl` is not available inside the container, test with an n8n HTTP Request node instead.

---

## Common Issues

### n8n asks to register again

This means n8n is using a new or different `/home/node/.n8n` storage folder.

For a temporary production test, this is normal.

For your existing workflows, make sure the same n8n data folder is mounted to:

```text
/home/node/.n8n
```

### n8n cannot find `/home/node/.n8n-files`

The project `data/` folder is not mounted into n8n.

Fix the n8n volume mapping:

```text
/path/to/project/data:/home/node/.n8n-files
```

### n8n cannot reach the API

Use the correct URL depending on your setup:

```text
http://literature-feed-api:8000/run_feed
```

for production Compose.

```text
http://host.docker.internal:8000/run_feed
```

for a standalone n8n container calling a host API.

### Attachment node fails

Check that the generated file exists inside n8n:

```bash
docker exec -it literature-n8n ls -lah /home/node/.n8n-files/bibtex
```

Also confirm that your n8n expression points to the correct upstream node name.

---

## GitHub Safety Notes

Do not commit:

```text
.env
.n8n/
.ollama/
data/feeds/*
data/digests/*
data/bibtex/*
data/ris/*
data/logs/*
data/pdfs/*
```

Commit only generic documentation, workflow notes, example configuration files, and screenshots that do not expose credentials or private email addresses.
