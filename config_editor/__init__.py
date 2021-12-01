import logging
import os
import voluptuous as vol
from homeassistant.components import websocket_api
from atomicwrites import AtomicWriter

DOMAIN = 'config_editor'
_LOGGER = logging.getLogger(__name__)


async def async_setup(hass, config):
    hass.components.websocket_api.async_register_command(websocket_create)
    hass.states.async_set(DOMAIN+".version", 1)
    return True


@websocket_api.require_admin
@websocket_api.async_response
@websocket_api.websocket_command(
    {
        vol.Required("type"): DOMAIN+"/ws",
        vol.Required("action"): str,
        vol.Required("file"): str,
        vol.Required("data"): str,
    }
)
async def websocket_create(hass, connection, msg):
    action = msg["action"]
    yamlname = "tmptest.yaml"
    if (msg["file"].endswith(".yaml")):
        yamlname = msg["file"]
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
                {'msg': res+': '+fullpath, 'file': yamlname, 'data': content}
            )

    elif (action == 'save'):
        _LOGGER.info('Saving '+fullpath)
        content = msg["data"]
        res = "Saved"
        try:
            with AtomicWriter(fullpath, overwrite=True).open() as fdesc:
                os.fchmod(fdesc.fileno(), 0o644)
                fdesc.write(content)
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
        listyaml = [
            f for f in os.listdir(dirnm)
            if os.path.isfile(os.path.join(dirnm, f)) and
            f.endswith(".yaml")
        ]
        listdeep = [
            d for d in os.listdir(dirnm)
            if os.path.isdir(os.path.join(dirnm, d))
        ]
        if (len(listdeep) > 0):
            for d in listdeep:
                deep = os.path.join(dirnm, d)
                sublist = [
                    f for f in os.listdir(deep)
                    if os.path.isfile(os.path.join(deep, f)) and
                    f.endswith(".yaml")
                ]
                if (len(sublist) > 0):
                    for x in sublist:
                        listyaml.append(os.path.join(d, x))
        if (len(listyaml) < 1):
            listyaml = ['list_error.yaml']
        connection.send_result(
            msg["id"],
            {'msg': str(len(listyaml))+' File(s)', 'file': listyaml}
        )
