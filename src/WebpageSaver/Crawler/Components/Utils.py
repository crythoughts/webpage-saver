from yarl import URL

def toURLWithoutMeaninglessDiffs(url: str):
    u = URL(url)
    new_host = u.host
    if u.host.startswith('www.'):
        new_host = u.host[4:]

    return u.with_host(new_host).with_scheme('').human_repr()[2:]
