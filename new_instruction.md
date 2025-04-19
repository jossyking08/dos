Configure Security Group:

Open the AWS EC2 console
Select your instance and go to the "Security" tab
Click on the security group link
Add an inbound rule:

Type: Custom TCP
Port Range: 8000
Source: Your IP address (or 0.0.0.0/0 for any IP, but this is less secure)
Description: Django App

Get your EC2 instance's public IP or DNS:

Find your instance's public IP/DNS in the EC2 dashboard
Access your application by visiting: http://your-ec2-public-ip:8000



If you want to use Nginx as a reverse proxy (recommended for production):

sudo apt update
sudo apt install -y nginx

sudo nano /etc/nginx/sites-available/django_app


server {
    listen 80;
    server_name your-ec2-public-ip;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}


sudo ln -s /etc/nginx/sites-available/django_app /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx


chmod +x setup_server.sh

sudo ufw allow 8000
./setup_server.sh


./startup.sh
