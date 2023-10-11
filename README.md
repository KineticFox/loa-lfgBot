# loa-lfgBot
A recreation of the famous lfg-Bot but only for Lost Ark (by now)

# User-Guide
1. ```/register_char``` -- registers one of many of your chars and registers your user if not exists
2. Now you are good to go and you can join and create Groups/Raids

- with ```/show_chars``` you can get an overview of your registered chars
- with ```/lfg``` you create a looking-for-group lobby


# Setup
- you need a mariadb container running (will be add to the compose file in the future)
- create inside the mariadb a databse
- enter the mariadb infomations into the compose file
```bash
    docker volume create 'bot-date'
    docker volume create 'bot-ressources'
    docker create --name temp -v bot-ressources:/ressources busybox
    sudo docker cp . temp:/ressources
    docker rm temp
    docker create --name temp -v bot-data:/ressources busybox
    sudo docker cp . temp:/data
    docker rm temp
    docker compose up --build
    sudo docker cp . 'container name':/data
    sudo docker cp . 'container name':/ressources
```