### Installation

To install this app, you should:

1. Clone this repo into some folder and cd into it.
2. Create virtual environment:

```
> python -m venv venv
```

3. Activate it:

```
> .\venv\Scripts\Activate.ps1
```
4. cd into `src`.
5. Install dependencies:

```
> pip install -e .
```

6. Run server:

```
> python server.py
```

It will start on `http://127.0.0.1:7514/`.

#### Change port

To change host and port, pass `server.host` and `server.port` in config.
