import logging
import os
import voluptuous as vol
from homeassistant.components import websocket_api
from atomicwrites import AtomicWriter

DOMAIN = 'config_editor'
_LOGGER = logging.getLogger(__name__)


async def async_setup(hass, config):
    hass.components.websocket_api.async_register_command(websocket_create)
    hass.states.async_set(DOMAIN+".version", 4)
    return True


@websocket_api.require_admin
@websocket_api.async_response
@websocket_api.websocket_command(
    {
        vol.Required("type"): DOMAIN+"/ws",
        vol.Required("action"): str,
        vol.Required("file"): str,
        vol.Required("data"): str,
        vol.Required("ext"): str,
        vol.Optional("depth", default=2): int
    }
)
async def websocket_create(hass, connection, msg):
    action = msg["action"]
    ext = msg["ext"]
    if ext not in ["yaml","py","json","conf","js","txt","log","css","all"]:
        ext = "yaml"

    def extok(e):
        if len(e)<2:
            return False
        return ( ext == 'all' or e.endswith("."+ext) )

    def rec(p, q):
        r = [
            f for f in os.listdir(p) if os.path.isfile(os.path.join(p, f)) and
            extok(f)
        ]
        for j in r:
            p = j if q == '' else os.path.join(q, j)
            listyaml.append(p)

    def drec(r, s):
        for d in os.listdir(r):
            v = os.path.join(r, d)
            if os.path.isdir(v):
                p = d if s == '' else os.path.join(s, d)
                if(p.count(os.sep) < msg["depth"]) and ( ext == 'all' or p != 'custom_components' ):
                    rec(v, p)
                    drec(v, p)

    yamlname = msg["file"].replace("../", "/").strip('/')

    if not extok(msg["file"]):
        yamlname = "temptest."+ext
        
    fullpath = hass.config.path(yamlname)
    if (action == 'load'):
        _LOGGER.info('Loading '+fullpath)
        content = ''
        res = 'Loaded'
        try:
            with open(fullpath, encoding="utf-8") as fdesc:
                content = fdesc.read()
        except:
            res = 'Reading Failed'
            _LOGGER.exception("Reading failed: %s", fullpath)
        finally:
            connection.send_result(
                msg["id"],
                {'msg': res+': '+fullpath, 'file': yamlname, 'data': content, 'ext': ext}
            )

    elif (action == 'save'):
        _LOGGER.info('Saving '+fullpath)
        content = msg["data"]
        res = "Saved"
        try:
            dirnm = os.path.dirname(fullpath)
            if not os.path.isdir(dirnm):
                os.makedirs(dirnm, exist_ok=True)
            try:
                stat_res = os.stat(fullpath)
                mode = stat_res.st_mode
                uid = stat_res.st_uid
                gid = stat_res.st_gid
            except:
                mode = 0o666
                uid = 0
                gid = 0
            with AtomicWriter(fullpath, overwrite=True).open() as fdesc:
                fdesc.write(content)
            with open(fullpath, 'a') as fdesc:
                try:
                    os.fchmod(fdesc.fileno(), mode)
                    os.fchown(fdesc.fileno(), uid, gid)
                except:
                    pass
        except:
            res = "Saving Failed"
            _LOGGER.exception(res+": %s", fullpath)
        finally:
            connection.send_result(
                msg["id"],
                {'msg': res+': '+fullpath}
            )

    elif (action == 'list'):
        dirnm = os.path.dirname(hass.config.path(yamlname))
        listyaml = []
        rec(dirnm, '')
        if msg["depth"]>0:
            drec(dirnm, '')
        if (len(listyaml) < 1):
            listyaml = ['list_error.'+ext]
        connection.send_result(
            msg["id"],
            {'msg': str(len(listyaml))+' File(s)', 'file': listyaml, 'ext': ext}
        )
