# Contributing

👍🎉 First off, thank you for taking the time to contribute! 🎉👍

The following is a set of guidelines for contributing. These are just guidelines, not rules. Use your best judgment, and feel free to propose changes to this document in a pull request.

## What Should I Know Before I Get Started?

If you're new to GitHub and working with open source repositories, this section will be helpful. Otherwise, you can skip to learning how to [set up your dev environment](#set-up-your-dev-environment)

### Code of Conduct

This project adheres to the [Contributor Covenant](./CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

Please report unacceptable behavior to one of the [Code Owners](./.github/CODEOWNERS).

### How Do I Start Contributing?

The below workflow is designed to help you begin your first contribution journey. It will guide you through creating and picking up issues, working through them, having your work reviewed, and then merging.

Help on inner source projects is always welcome and there is always something that can be improved. For example, documentation (like the text you are reading now) can always use improvement, code can always be clarified, variables or functions can always be renamed or commented on, and there is always a need for more test coverage. If you see something that you think should be fixed, take ownership! Here is how you get started:

## How Can I Contribute?

When contributing, it's useful to start by looking at [issues](https://github.com/IBM/import-tracker/issues). After picking up an issue, writing code, or updating a document, make a pull request and your work will be reviewed and merged. If you're adding a new feature, it's best to [write an issue](https://github.com/IBM/import-tracker/issues/new?assignees=&labels=&template=feature_request.md&title=) first to discuss it with maintainers first.

### Reporting Bugs

This section guides you through submitting a bug report. Following these guidelines helps maintainers and the community understand your report ✏️, reproduce the behavior 💻, and find related reports 🔎.

#### How Do I Submit A (Good) Bug Report?

Bugs are tracked as [GitHub issues using the Bug Report template](https://github.com/IBM/import-tracker/issues/new?assignees=&labels=&template=bug_report.md&title=). Create an issue on that and provide the information suggested in the bug report issue template.

### Suggesting Enhancements

This section guides you through submitting an enhancement suggestion, including completely new features, tools, and minor improvements to existing functionality. Following these guidelines helps maintainers and the community understand your suggestion ✏️ and find related suggestions 🔎

#### How Do I Submit A (Good) Enhancement Suggestion?

Enhancement suggestions are tracked as [GitHub issues using the Feature Request template](https://github.com/IBM/import-tracker/issues/new?assignees=&labels=&template=feature_request.md&title=). Create an issue and provide the information suggested in the feature requests or user story issue template.

#### How Do I Submit A (Good) Improvement Item?

Improvements to existing functionality are tracked as [GitHub issues using the User Story template](https://github.com/IBM/import-tracker/issues/new?assignees=&labels=&template=user-story.md&title=). Create an issue and provide the information suggested in the feature requests or user story issue template.

## Development

### Set up your dev environments

#### Using Docker

The easiest way to get up and running is to use the dockerized development environment which you can launch using:

```sh
make develop
```

Within the `develop` shell, any of the `make` targets that do not require `docker` can be run directly. The shell has the local files mounted, so changes to the files on your host machine will be reflected when commands are run in the `develop` shell.

#### Locally

You can also develop locally using standard python development practices. You'll need to install the dependencies for the unit tests. It is recommended that you do this in a virtual environment such as [`conda`](https://docs.conda.io/en/latest/miniconda.html) or [`pyenv`](https://github.com/pyenv/pyenv) so that you avoid version conflicts in a shared global dependency set.

```sh
pip install -r requirements_test.txt
```

### Run unit tests

Running the tests is as simple as:

```sh
make test
```

If you want to use the full set of [`pytest` CLI arguments](https://docs.pytest.org/en/6.2.x/usage.html), you can run the `scripts/run_tests.sh` script directly with any arguments added to the command. For example, to run only a single test without capturing output, you can do:

```sh
./scripts/run_tests.sh \
    test/test_lazy_import_errors.py \
    -k test_lazy_import_happy_package_with_sad_optionals \
    -s
```

### Code formatting

This project uses [pre-commit](https://pre-commit.com/) to enforce coding style using [black](https://github.com/psf/black). To set up `pre-commit` locally, you can:

```sh
pip install pre-commit
```

Coding style is enforced by the CI tests, so if not installed locally, your PR will fail until formatting has been applied.

## Your First Code Contribution

Unsure where to begin contributing? You can start by looking through these issues:

- Issues with the [`good first issue` label](https://github.com/IBM/import-tracker/issues?q=is%3Aopen+is%3Aissue+label%3A%22good+first+issue%22) - these should only require a few lines of code and are good targets if you're just starting contributing.
- Issues with the [`help wanted` label](https://github.com/IBM/import-tracker/issues?q=is%3Aopen+is%3Aissue+label%3A%22help+wanted%22) - these range from simple to more complex, but are generally things we want but can't get to in a short time frame.

### How to contribute

To contribute to this repo, you'll use the Fork and Pull model common in many open source repositories. For details on this process, watch [how to contribute](https://egghead.io/courses/how-to-contribute-to-an-open-source-project-on-github).

When ready, you can create a pull request. Pull requests are often referred to as "PR". In general, we follow the standard [github pull request](https://help.github.com/en/articles/about-pull-requests) process. Follow the template to provide details about your pull request to the maintainers.

Before sending pull requests, make sure your changes pass tests.

#### Code Review

Once you've [created a pull request](#how-to-contribute), maintainers will review your code and likely make suggestions to fix before merging. It will be easier for your pull request to receive reviews if you consider the criteria the reviewers follow while working. Remember to:

- Run tests locally and ensure they pass
- Follow the project coding conventions
- Write detailed commit messages
- Break large changes into a logical series of smaller patches, which are easy to understand individually and combine to solve a broader issue

## Releasing (Maintainers only)

The responsibility for releasing new versions of the libraries falls to the maintainers. Releases will follow standard [semantic versioning](https://semver.org/) and be hosted on [pypi](https://pypi.org/project/import-tracker/).
