# 🤖 SMC Crypto Trading Bot (24/7 Cloud Ready)

Système de Day Trading quantitatif automatisé basé sur les **Smart Money Concepts (SMC)**, le **Cumulative Volume Delta (CVD)** et la gestion asymétrique du risque.

---

## 🚀 Déploiement sur Render en 2 minutes (100% Gratuit)

1. Créez un compte gratuit sur [Render.com](https://render.com).
2. Cliquez sur **New +** > **Web Service**.
3. Connectez votre compte GitHub et sélectionnez ce dépôt (`crypto-bot-smc`).
4. Remplissez les champs de configuration :
   - **Name** : `crypto-bot-smc`
   - **Environment** : `Python 3`
   - **Build Command** : `pip install -r requirements.txt`
   - **Start Command** : `python bot_runner.py`
   - **Instance Type** : `Free` (0 $/mois)
5. Dans la section **Advanced** > **Environment Variables**, ajoutez :
   - `DISCORD_WEBHOOK_URL` : Votre URL de Webhook Discord
6. Cliquez sur **Create Web Service**.

> 🎉 **C'est tout !** Render va installer les dépendances et démarrer le bot 24h/24 dans le cloud.

---

## ⚡ Maintenir le service actif 24/24 (Anti-Sleep)

Le forfait gratuit de Render met en veille les Web Services après 15 minutes sans requête HTTP. Pour qu'il scanne sans discontinuer :
1. Créez un compte gratuit sur [UptimeRobot.com](https://uptimerobot.com) ou [cron-job.org](https://cron-job.org).
2. Ajoutez un moniteur HTTP (ping toutes les 5 à 10 minutes) vers l'URL fournie par Render (ex : `https://crypto-bot-smc.onrender.com`).
3. Le serveur HTTP intégré répondra `200 OK` et le bot ne s'endormira jamais !
