# Import Tracker
`Import Tracker` is a Python package offering a number of cabilities related to tracking and managing optional dependencies in Python projects. Specifically, this project enables developers to:

- Enable lazy imports in their Python projects to prevent code from crashing when uninstalled imports are imported, but not utilized. This can be helpful in large projects, especially those which incorporate lots of hierarchical wild imports, as importing the top level package of such projects can often bring a lot of heavy dependencies into `sys.modules`.

- Track the dependencies of their Python projects to identify which subpackages are leveraging which dependencies, and so on.


### Integrating Import Tracker into your projects
In order to integrate `Import Tracker` into your project, you'll generally need to replace normal imports in your top level package initialization with calls to `import_tracker.import_module`. Such imports will then be subject to the aforementioned behaviors, which are dependent on the value of `IMPORT_TRACKER_MODE`. The best sample of how to do this can be found in the [initialization file](./test/sample_libs/sample_lib/__init__.py) for the `sample_lib` leveraged by this project for testing.


### Running Import Tracker
Once you have integrated `Import Tracker` into your project, you can leverage it in your project. In general, the functionality of module imports through `Import Tracker` are controlled by setting the `IMPORT_TRACKER_MODE` environment variable to one of the following values. 

- `LAZY`: When a module is imported, build a lazy module wrapper that will *only* try to import the module if an attribute of the wrapped module is accessed.
- `BEST_EFFORT`<sup>[†](#footnote)</sup>: When a module is imported, actually do the import, but wrap it with lazy error semantics.
- `PROACTIVE`: When a module is imported, simply import and return it. This is functionally equivalent to invoking [importlib.import_module](https://docs.python.org/3/library/importlib.html#importlib.import_module).
- `TRACKING`: Track the dependencies of a module and dump the results to a JSON file.

Depending on your choice of value for `IMPORT_TRACKER_MODE`, you may want to simply run your project code (i.e., for the use-case of having lazy imports), or you may want to run the `Import Tracker` module directly to dig into your dependencies. To understand how to accomplish the latter, you can run the following command.

`python3 -m import_tracker --help`

Currently, the easiest way to run `Import Tracker` on a project is to add that project onto your `PYTHONPATH` and invoke the main entrypoint, as shown below.
```bash
PYTHONPATH=$PYTHONPATH:$PWD/src:$PWD/test/sample_libs \
IMPORT_TRACKER_MODE=LAZY \
python3 -m import_tracker -n sample_lib
```

<a name="footnote">†</a>: Currently, `BEST_EFFORT` is the default behavior if `IMPORT_TRACKER_MODE` is unset.

### How to Run Tests
In order to run the tests, you'll need to first install the test dependencies as shown below.
```
pip3 install -r requirements_test.txt
```

Then, you can run the unit tests as shown below.
```python3
python3 -m pytest test
```
