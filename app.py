
app = "energy-tracking"
primary_region = "lhr"

[env]
  PORT = "8080"   # uvicorn and the service will use this port

# Define the process called "app" that will run your FastAPI app
[processes]
  app = "uvicorn app:app --host 0.0.0.0 --port 8080"

# Define the service (HTTP listener) and link it to the "app" process
[[services]]
  internal_port = 8080
  protocol = "tcp"
  processes = ["app"]   # <<< this line solves the error

  [[services.ports]]
    handlers = ["http"]
    port = 80

  [[services.ports]]
    handlers = ["tls", "http"]
    port = 443
