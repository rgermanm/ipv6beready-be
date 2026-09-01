# IPv6BeReady Backend

FastAPI backend for provisioning and managing container-based network labs. Lab catalog and sessions are stored in MongoDB.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Run

```bash
uvicorn app.main:app --reload --port 8000
```

API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

## API Endpoints

### Lab catalog

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/labs` | List all labs |
| `GET` | `/api/labs/{lab_id}` | Lab definition with exercises and container formula |
| `GET` | `/api/labs/{lab_id}/exercises` | Exercise list for a lab |

### Lab sessions (container lifecycle)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/labs/{lab_id}` | Create and start a container lab using the lab's formula |
| `GET` | `/api/labs/{lab_id}/session` | Get active session status |
| `DELETE` | `/api/labs/{lab_id}` | Terminate the active container |

## Lab formula

Each lab includes a `formula` object that describes how the server provisions the environment.
Docker labs use a container image; clab labs include a `yml` field with the containerlab topology
and deploy remotely via SSH.

The `POST /api/labs/{lab_id}` endpoint reads the lab from MongoDB and deploys using `formula.clab.path` (the folder on the lab server that contains the `.clab.yml`).

Example for the static routing lab:

```
path: /home/deploy/labs/networking001/lab-rutas_estaticas
topology_file: rutas_estaticas.clab.yml
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `MOCK_CONTAINERS` | `false` | Skip Docker/clab and simulate container startup |
| `LAB_HOST` | `localhost` | Hostname returned for local Docker labs |
| `CLAB_REMOTE_HOST` | `66.97.37.101` | SSH host for containerlab deploy |
| `CLAB_REMOTE_PORT` | `5412` | SSH port |
| `CLAB_REMOTE_USERNAME` | `root` | SSH username |
| `CLAB_REMOTE_PASSWORD` | — | SSH password (required for clab labs) |
| `MONGODB_URI` | `mongodb://admin:...@127.0.0.1:27019/?authSource=admin` | MongoDB URI (host rewritten when tunnel is on) |
| `MONGODB_DB` | `ipv6beready` | Database name |
| `MONGODB_SSH_TUNNEL` | `true` | Tunnel Mongo over SSH (needed from your laptop) |
| `DOCKER_NETWORK` | `ipv6beready-fe_lab-net` | Docker network for local container labs |
| `CORS_ORIGINS` | `["http://localhost:3000"]` | Allowed frontend origins |

## Development

Set `MOCK_CONTAINERS=true` in `.env` to run without Docker. Sessions will report as running on port `2222`.

For real containers, build lab images from the frontend repo:

```bash
cd ../ipv6beready-fe
docker compose build
```

Then set `MOCK_CONTAINERS=false` and ensure the `DOCKER_NETWORK` matches your compose network.

## MongoDB

`mongo-ipv6beready-prod` is a Docker container on the VPS. Port **27019 is not reachable from the internet**, so Compass and a direct URI will fail.

The backend opens an SSH tunnel automatically (`MONGODB_SSH_TUNNEL=true`) using the same SSH host as the labs (`CLAB_REMOTE_*`) to `127.0.0.1:27019` on the VPS.

For Compass, open a tunnel in another terminal:

```bash
./mongo-tunnel.sh
```

Then connect with TLS **off**:

```
mongodb://admin:I6brReady--k8mQ2nP91x@127.0.0.1:27019/?authSource=admin
```

When the API runs on the VPS Docker network, set `MONGODB_SSH_TUNNEL=false` and:

```
mongodb://admin:I6brReady--k8mQ2nP91x@mongo-ipv6beready-prod:27017/?authSource=admin
```
