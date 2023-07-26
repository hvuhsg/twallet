# TWallet

Minimal TON wallet on Telegram (Official Bot https://t.me/TONPrivateWalletBot)

---

### Run

#### clone
```commandline
git clone https://github.com/hvuhsg/twallet
```
#### build docker image
```commandline
cd twallet
docker build -t twallet .
```
#### run docker container
```shell
docker run -it -e BOT_TOKEN='' -e TONCENTER_API_KEY='' twallet:latest
```
