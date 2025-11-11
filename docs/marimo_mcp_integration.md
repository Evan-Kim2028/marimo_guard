# Marimo MCP Integration Guide

## Overview

spice-mcp includes bidirectional integration with marimo's Model Context Protocol (MCP) server, enabling:

- **Session Management**: Track active marimo notebook sessions
- **Health Monitoring**: Background monitoring of notebook errors
- **Refresh Coordination**: Warn when refreshing data for active notebooks
- **Bidirectional Communication**: marimo chat panel can use spice-mcp tools

## Architecture

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│  spice-mcp  │◄────────┤ Marimo MCP   │────────►│   marimo    │
│   Server    │  HTTP   │   Client     │  HTTP   │   Server    │
└─────────────┘         └──────────────┘         └─────────────┘
      │                        │                        │
      │                        │                        │
      └────────────────────────┴────────────────────────┘
                    MCP Protocol
```

### Components

1. **MarimoMCPClient**: HTTP client connecting to marimo's MCP server endpoint
2. **NotebookSessionService**: Tracks and coordinates active notebook sessions
3. **NotebookHealthMonitor**: Background polling for notebook errors
4. **MCP Tools**: `marimo_sessions` and `marimo_health` tools exposed by spice-mcp

## Configuration

### Environment Variables

```bash
# Enable/disable marimo MCP integration (default: true)
SPICE_MARIMO_MCP_ENABLED=true

# Marimo MCP server URL (default: http://localhost:2718/mcp/server)
SPICE_MARIMO_MCP_URL=http://localhost:2718/mcp/server

# Marimo MCP server port (default: 2718)
SPICE_MARIMO_MCP_PORT=2718

# Enable health monitoring (default: true)
SPICE_MARIMO_HEALTH_MONITORING=true

# Health check interval in seconds (default: 60)
SPICE_MARIMO_HEALTH_INTERVAL=60

# Connection timeout in seconds (default: 5)
SPICE_MARIMO_CONNECTION_TIMEOUT=5
```

### Default Configuration

The integration is enabled by default. If marimo is not running, the integration gracefully degrades without errors.

## Usage

### Querying Active Notebooks

Use the `marimo_sessions` tool to list active notebook sessions:

```python
# Via MCP tool call
result = mcp__spice_mcp__marimo_sessions()

# Response:
# {
#   "ok": True,
#   "sessions": [
#     {
#       "session_id": "abc123",
#       "file_path": "/path/to/notebook.py",
#       "status": "active"
#     }
#   ],
#   "count": 1
# }
```

### Checking Notebook Health

Use the `marimo_health` tool to check for errors in active notebooks:

```python
# Via MCP tool call
result = mcp__spice_mcp__marimo_health()

# Response:
# {
#   "ok": True,
#   "total_errors": 2,
#   "notebooks": {
#     "/path/to/notebook.py": ["Error message 1", "Error message 2"]
#   },
#   "healthy": False
# }
```

### Session-Aware Refresh

When refreshing a notebook that's currently open, spice-mcp will warn you:

```python
result = mcp__spice_mcp__dune_marimo({
    "action": "refresh",
    "report_path": "my_notebook.py"
})

# Response includes session_warning if notebook is active:
# {
#   "ok": True,
#   "report_path": "...",
#   "session_warning": "Notebook is currently open in marimo (session: abc123). Refreshing data may cause conflicts..."
# }
```

## Exposing spice-mcp to marimo

To enable marimo's chat panel to use spice-mcp tools:

### 1. Start spice-mcp MCP Server

```bash
spice-mcp
```

### 2. Configure marimo

Create or edit `.marimo.toml` in your project root:

```toml
[mcp]
presets = []

[mcp.servers.spice_mcp]
type = "stdio"
command = "uvx"
args = ["spice-mcp"]
env = {"DUNE_API_KEY": "your-api-key-here"}
```

### 3. Restart marimo

Restart marimo to load the new MCP server configuration. The spice-mcp tools will now be available in marimo's chat panel.

## Background Health Monitoring

When enabled, spice-mcp periodically checks for errors in active notebooks:

- **Polling Interval**: Configurable (default: 60 seconds)
- **Logging**: Errors are logged as warnings
- **Graceful Degradation**: Monitoring continues even if some checks fail

### Disabling Health Monitoring

```bash
SPICE_MARIMO_HEALTH_MONITORING=false
```

## Troubleshooting

### Marimo MCP Server Not Available

**Symptoms**: `marimo_sessions` returns empty list, `marimo_health` returns errors.

**Solutions**:
1. Ensure marimo is running with `--mcp` flag:
   ```bash
   marimo edit notebook.py --mcp --no-token
   ```
2. Check marimo is listening on the expected port (default: 2718)
3. Verify `SPICE_MARIMO_MCP_URL` matches marimo's MCP server URL

### Connection Timeouts

**Symptoms**: Health checks fail with timeout errors.

**Solutions**:
1. Increase `SPICE_MARIMO_CONNECTION_TIMEOUT` (default: 5 seconds)
2. Check network connectivity to marimo server
3. Verify marimo MCP server is accessible

### Health Monitor Not Starting

**Symptoms**: No health check logs, `marimo_health` tool returns "not enabled".

**Solutions**:
1. Verify `SPICE_MARIMO_HEALTH_MONITORING=true`
2. Check server logs for initialization errors
3. Ensure marimo MCP client initialized successfully

## API Reference

### MarimoMCPClient

```python
from spice_mcp.adapters.marimo.client import MarimoMCPClient

client = MarimoMCPClient(
    base_url="http://localhost:2718/mcp/server",
    http_client=http_client,
    connection_timeout=5,
)

# Get active notebooks
notebooks = client.get_active_notebooks()

# Get errors summary
errors = client.get_errors_summary()

# Health check
is_healthy = client.health_check()
```

### NotebookSessionService

```python
from spice_mcp.service_layer.session_service import NotebookSessionService

service = NotebookSessionService(marimo_client)

# Get all active sessions
sessions = service.get_active_sessions()

# Check if notebook is active
is_active = service.is_notebook_active(Path("notebook.py"))

# Get session for notebook
session = service.get_session_for_notebook(Path("notebook.py"))

# Get warning if active
warning = service.warn_if_active(Path("notebook.py"))
```

### NotebookHealthMonitor

```python
from spice_mcp.service_layer.health_monitor import NotebookHealthMonitor

monitor = NotebookHealthMonitor(
    marimo_client=client,
    poll_interval=60,
    enabled=True,
)

# Start background monitoring
await monitor.start()

# Perform single health check
health = await monitor.check_health()

# Stop monitoring
await monitor.stop()
```

## Best Practices

1. **Enable Health Monitoring**: Keep background monitoring enabled for production use
2. **Check Sessions Before Refresh**: Use `marimo_sessions` to verify notebook status before refreshing
3. **Handle Warnings**: Respect `session_warning` in refresh responses
4. **Graceful Degradation**: Always handle cases where marimo is not running
5. **Configure Timeouts**: Adjust connection timeouts based on your network conditions

## Related Documentation

- [Marimo MCP Documentation](https://docs.marimo.io/guides/editor_features/mcp/)
- [Reports Guide](./reports.md)
- [Tools Reference](./tools.md)

