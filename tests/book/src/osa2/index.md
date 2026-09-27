# Työkalut

Toisen osan etusivu.

Komentorivilohkot: kehotteet ja tulosteet näkyvät sivulla, mutta
kopiointinappi kopioi vain komennot (copy.js). Komento jatkuu
\-rivinvaihdon yli ja heredocin loppuun, ja kommentit säilyvät.

```console
$ docker run --rm \
    hello-world
Hello from Docker!
$ docker build -t kaiku .
#5 [1/2] FROM docker.io/library/python:3.13-slim
#5 DONE 0.1s
$ ls  # kommentti jää
$ python3 - <<'EOF'
# Pythonin kommentti jää
print("hei")
EOF
hei
```

Kehote kontin komentotulkissa, ja komennossa $- ja %-merkki.

```console
root@kontti:/app# kill %1
[1]+  Terminated              python kaiku.py
root@kontti:/app# echo $?
0
root@kontti:/app#
```

Pelkkä `#` on rootin kehote vain, kun lohkossa ei ole muita kehotteita.

```console
# apt-get install -y curl
```

```console
$ cat Dockerfile
# syntax=docker/dockerfile:1
FROM python:3.13-slim
```

Pelkkä tuloste ja muut kielet kopioidaan sellaisenaan.

```console
Hello from Docker!
```

```python
# kommentti
print("hei")  # rivin lopussa
```
