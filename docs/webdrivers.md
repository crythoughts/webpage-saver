### Webdrivers

To install chromedriver, go to `/webdrivers` URL and click on "Download latest chromedriver".

Also webdriver can be stopped or set default on this page.

To use existing executable on your drive as webdriver, add to `webdrivers` in `config` new dict with:

```json
{
    "channel": "Stable",
    "version": "2",
    "platform": "win",
    "shell_path": "" // path
}
```

You can also specify `args`, `user_data_dir` and `user_agent`.

### CDP

Set `webdriver_type` key to "CDP" and set `cdp_endpoint` if needed.

Also, you need to start Chrome with `--remote-debugging-port=9222 --user-data-dir="[another folder]"` flags.
