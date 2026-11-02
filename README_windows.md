# Ch-Lat: Charter Light Annotation Tool

## FYI only: how the container image was built (on Linux):

```bash
sudo docker image rm ch-lat;  sudo docker build --network host --tag ch-lat .
```

## Run on your Windows system

Requirements:

+ [Windows Subsystem for Linux (WSL)](https://learn.microsoft.com/en-us/windows/wsl/install)
+ [Docker desktop](https://desktop.docker.com/win/main/amd64)

1. In a folder of your choice (say, `C:\Users\nicolas\transcription_review`), download the following 3 files:

+ `ch-lat.tar.gz` (the container image, no need to untar)
+ `dev` (the environment variable definitions, to be used by the container when running)
+ `samples.zip` (a couple dozens of samples, for testing purpose)

2. Launch the *Windows Powershell (PS)* in a terminal and load the container image:

```bash
cd C:\Users\nicolas\transcription_review
docker image load --input ch-lat.tar.gz
```

3. Unzip the image+transcription samples:

```ps
Expand-Archive samples.zip -DestinationPath .
```

This creates a `.\samples` subfolder with images (`*.img.jpg`), first-stage (`*.htr.pregt.json`) and second-stage (`*.htr.gt.json`) transcriptions.

2. Start the application:

```bash
docker run -v C:/Users/nicolas/transcription_review/samples:/fsdb_root --rm -it -p 5001:5001 --name ch-lat --env-file ./env ch-lat
```

The `env` file sets the environment variables read by the Docker-contained Flask server, as shown below:

```bash
FLASK_flat=1
FLASK_max_width=1200
FLASK_fsdb_root=/fsdb_root
```

The value of `FLASK_fsdb_root` is used by the Flask annotation app to find the location of the files to be annotated (images and metadata). The `-v` parameter passed to `docker run`
maps the actual location on the host (ie. your machine) to the virtual location in the Docker container (`/fsdb_root`).
The `env` file is not meant to be modified; to pass an alternate location for the work files, simply run docker with a different mapping, eg. `-v /tmp/myLocation:/fsdb_root`.

3. Finally, in the browser:

```
http://localhost:5001/alignment
```

## Debugging

Check the following in this order:

### 1. Has the image been loaded correctly?

```ps
docker image ls
```

Expected output:

```
IMAGE                ID             DISK USAGE   CONTENT SIZE   EXTRA
ch-lat:latest        8a06ff3bfe90        339MB         80.7MB
```

### 2. Server unreachable or timeout: is the container running?

```
docker container ls
```

Expected output:

```
CONTAINER ID   IMAGE     COMMAND                  CREATED          STATUS          PORTS     NAMES
c3816ed6ddba   ch-lat    "python3 -m flask --…"   19 seconds ago   Up 18 seconds             ch-lat
```


### 3. Error 404 (Failed to retrieve charters ids.): are the work files exposed to the container in the set location?

Log on the container:

```
docker exec -it ch-lat bash
```

In the container's (Linux) shell, type:

```
ls /fsdb_root
```

and check that the expected files are visible. If they're not, verify the actual (host) location and then the mapping (`-v` option for `docker run`).


