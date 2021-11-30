# Standard
import json

# Third Party
import yaml

# First Party
import alog

log = alog.use_channel("SUB3")


def yaml_to_json(fname, *args, **kwargs):
    """Yaml file to json string"""
    log.debug("Opening %s", fname)
    with open(fname, "r") as handle:
        return yaml_to_jsons(handle.read(), *args, **kwargs)


def yaml_to_jsons(yaml_str, *args, **kwargs):
    """Yaml string to json string"""
    return json.dumps(yaml.safe_load(yaml_str, *args, **kwargs))


def json_to_yaml(fname, *args, **kwargs):
    """Json file to yaml string"""
    log.debug("Opening %s", fname)
    with open(fname, "r") as handle:
        return yaml.safe_dump(json.load(handle), *args, **kwargs)


def json_to_yamls(json_str, *args, **kwargs):
    """Json file to yaml string"""
    return yaml.safe_dump(json.loads(json_str), *args, **kwargs)
