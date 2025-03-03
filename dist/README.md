# Ch-Lat = Charter Line Annotation Tool

## How to use:

1. Download and unzip the sample dataset:


```bash
unzip fsdb_full_text_sample_100.zip
```
2. Download the container image

3. Load the image into Docker:

```bash
docker load ch-lat.docker.tar.gz
```

4. Run:

```bash
docker run -v /tmp/fsdb_full_text_sample_100:/fsdb_root --network host --rm -it --env-file ./.env ch-lat
```

5. In the browser:

```http://localhost:5000```
