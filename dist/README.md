

Load the container:


```bash
docker load ch-lat.docker.tar.gz
```


Run:

```bash
docker run -v /tmp/fsdb_full_text_sample_100:/fsdb_root --network host --rm -it --env-file ./.env ch-lat
```


