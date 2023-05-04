# stb

A universal tool for local microservice management

## Requirements

* [Poetry](https://python-poetry.org/) - Required for setup functionality 
* [Pyenv](https://github.com/pyenv/pyenv) - Optional

## Installation

```bash
pipx install stb-mnt
```

## Usage

### Setup

* To download and setup my_company/backend/service1 microservice as a subdirectory to the current working directory, use:

```bash
stb setup my_company/backend/service1
```

* To download and setup my_company/backend/service1 and my_company/backend/service2 as subdirectories to current working directory, use:

```bash
stb setup my_company/backend/service1 my_company/backend/service2
```

* To setup all backend services, use:

```bash
stb setup my_company/backend
```

Note that if you want to clone repositories, you must first set a `git_url` using `stb config set git_url` command

### Update

* To update .env file in accordance with .env.example in a microservice:

```bash
stb update env
```

* To synchronize service ports between all installed microservices (you can specify which ones will run locally with the `--local` option):

```bash
stb update ports
```

* To update poetry.lock file, install dependencies, stash current changes, checkout to master, pull from remote, and recreate databases:

```bash
stb update package -piucd
```

or  

```bash
stb update package --pull --update --checkout --reset-databases
```

### DB

* To upgrade migrations in a microservice:

```bash
stb db upgrade
```

* To create databases and upgrade its migrations in a microservice:

```bash
stb db create
```

* To drop databases in a microservice:

```bash
stb db drop
```

* To drop and recreate databases, and upgrade migrations in a microservice:

```bash
stb db reset
```

* To upgrade migrations in parallel for faster upgrades (useful for large monoliths with multiple databases), you can use the -p (--parallel) option:

```bash
stb db create -p
```
  
```bash
stb db reset -p
```
  
* To force dropping of databases in case another program is using them at the same time, you can use the -f (--force) option:

```bash
stb db drop -f
```
  
```bash
stb db reset -f
```
  
### Use

`stb use` allows you to take a company private package and install either a cloud version or a local version of it. STB will preserve all extras, automatically set package source, and will gracefully handle any issues that might happen while updating.

* To install a local version of `my_package` that is located at `../my_package`:

```bash
stb use ../my_package
```

* To install a local version of `my_package` that is located at `../my_package` in editable mode:

```bash
stb use ../my_package --editable
```

* To install a cloud version of `my_package` with tag `8.3.1`:

```bash
stb use "my_package==8.3.1"
```

* To install a cloud version of my_package with tag `8.3.1`, my_other_package with any tag higher than `1.2.3`, and my_third_package with any tag more than or equal to `4.5.6` and less than `5.0.0`:

```bash
stb use "my_package==8.3.1" "my_other_package>1.2.3" "my_third_package^4.5.6"
```

### Run

* To update and run the select services concurrently:

```bash
stb run service1 service2
```

### Config

* To set a git url for cloning:

```bash
stb config set git_url git@gitlab.my_company.com
```

### Graph

* To get a dependency graph of your microservices:

```bash
stb graph json my_company/backend/ my_company/infrastructure/
```

* To get a dependency graph of your microservices as an svg image (requires graphviz):

```bash
stb graph graphviz my_company/backend/ my_company/infrastructure/
```

### How directories are selected for update/db

For every update, you can specify:

1) A microservice directory, which will cause stb to update only that microservice
2) Several microservice directories, which will cause stb to update these microservices and integrate them together (for example, `update ports` assigns ports to local microservices and updates their links in other microservices to match the assigned ports)
3) A directory with multiple microservice subdirectories inside it, which is equivalent to (2) with the list of subdirectories as arguments
4) Nothing, which will choose the current working directory as the first argument and will be equivalent to (1) or (3)
