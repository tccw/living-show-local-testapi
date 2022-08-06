## Living Snow Testing API
This is a simple implementation of a containerized API that tries to replicate the behavior of the Living Snow API. It makes new features which need to upload/download records and photos easier to test locally.

## Running
Make sure docker and docker-compose are installed.

In the root of the project, run the following commands:
```
docker compose build && docker compose up
```

This will build the docker container for the API and then start the container. The API is mapped to `localhost:8080/`. To use the API while running a test build of Living Snow, edit the file `LivingSnowProject/src/constants/Service.ts` to change the service endpoints to:

```
const serviceEndpoint =
    "http://<the-local-ip-of-your-machine>:8080";
const photosBlobStorageEndpoint =
    "http://${the-local-ip-of-your-machine}:8080/api/blob";

```
You must use your local IPv4 address in order for test builds to route requests properly from your phone with `expo-go` or an Android or iOS simulator.