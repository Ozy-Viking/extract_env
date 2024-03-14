# Extract Env

A tool for extracting environment variables from compose files and adding them to .env files and replacing them with appropriated parameter expansion. It takes into account preferences for example compose.production.yaml and will produce a .env.production instead. Also, it checks for all 4 version of compose files [see regex for explanation](#regex).

## Example

### From

./docker-compose.local.yaml:

```yaml
...
environment:
  - MODE=Production
  - PASSWORD=SuperSecretDoNotShare 
...
```

### To

./docker-compose.local.yaml:

```yaml
...
environment:
  - MODE=${MODE}
  - PASSWORD=${PASSWORD} 
...
```

./.env.local:

```.env
MODE=Production
PASSWORD=SuperSecretDoNotShare
```

## CLI

```text
$ extract-env -h
Usage: extract-env [OPTIONS]

Options:
  -e, --env_folder PATH           Folder where the .env file/s to/are located.
                                  Default: ./
  --env-file-name PATH            Folder where the .env file/s to/are located.
                                  Default: .env
  --use-current-env / --no-use-current-env
                                  Use the current env files. Default: True
  -c, --compose-folder DIRECTORY  Folder where the compose file/s are located.
                                  Default: ./
  -C, --combine / -N, --no-combine
                                  Combine like named environment variables
                                  across services.  Default: True
  -p, --prefix TEXT               Prefix to add to all environment variable
                                  names.  Default: ""
  --postfix TEXT                  postfix to add to all environment variable
                                  names.  Default: ""
  -w, --write / -d, --dry-run     Write the environment variables to file.
                                  Default: True
  --display / --no-display        Displays the file output in the terminal.
                                  Default: False
  -u, --update-compose / -n, --no-update-compose
                                  Update the docker compose file with the new
                                  environment variable names.  Default: True
  -A, --all-files / -S, --selected-file
                                  Update the docker compose file with the new
                                  environment variable names.  Default: True
  -f, --compose_file FILE         Update this/these docker compose file/s with
                                  the new environment variable names. Used for
                                  specifying the paths of each file. When
                                  paths are specified it is assumed that
                                  --selected-files has been given.  Default:
                                  None
  -t, --test                      Test the program using files in the example
                                  folder.  Default: False
  -h, --help                      Show this message and exit.
```

## Mechanics

### Regex

#### Compose File

Used for checking for compose files and extracting their compose name if present.

```regex
(?P<compose_path>(?:docker-)?compose(?:\.(?P<compose_name>.*))?\.ya?ml)
```

#### Parameter Expansion

For detecting parameter expansion:

```regex
(?P<param>(?:^\$\{.*\}$)|(?:^\{\{.*\}\}$))
```

and for extracting the key from parameter expansion:

```regex
(?P<param>(?:^\$\{(?P<key1>.*)\}$)|(?:^\{\{(?P<key2>.*)\}\}$))
```
