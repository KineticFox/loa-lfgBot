# loa-lfgBot
A recreation of the famous lfg-Bot but only for Lost Ark (by now)

# User-Guide
1. ```/register_user``` -- registers your Discord-User to the Bot and Database
2. ```/register_char``` -- registers one of many of your chars
3. Now you are good to go and you can join and create Groups/Raids

- with ```/show_chars``` you can get an overview of your registered chars
- with ```/lfg``` you create a looking-for-group lobby


# Setup
- ```bash
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