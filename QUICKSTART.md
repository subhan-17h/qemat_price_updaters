# 🎯 AWS Free Tier - Quick Start Guide

Get your Price Updater running on AWS EC2 Free Tier in 30 minutes!

---

## 📋 What You Get

- ✅ **FREE for 12 months** - No charges for 3-day run
- ✅ **750 hours/month** - More than enough
- ✅ **t2.micro instance** - 1 vCPU, 1 GB RAM
- ✅ **30 GB storage** - Plenty for logs and outputs
- ✅ **No timeout limits** - Runs continuously

---

## 🚀 Quick Setup (30 Minutes)

### Step 1: Create AWS Account (5 min)
```
→ Visit: https://aws.amazon.com/free
→ Sign up (credit card needed, won't charge in free tier)
→ Get 12 months free tier access
```

### Step 2: Launch EC2 Instance (10 min)

1. **Go to EC2 Console**: https://console.aws.amazon.com/ec2
2. **Click "Launch Instance"**
3. **Configure:**
   ```
   Name: price-updater
   
   OS: Ubuntu Server 22.04 LTS (Free tier)
   
   Instance type: t2.micro (1 vCPU, 1GB) ✅ Free tier
   
   Key pair: Create new
     → Name: price-updater-key
     → Type: RSA
     → Format: .pem
     → Download and save!
   
   Network: Allow SSH from My IP
   
   Storage: 20 GB gp3
   ```
4. **Click "Launch Instance"**
5. **Note your Public IP** (e.g., 3.80.123.45)

### Step 3: Connect to Instance (2 min)

```bash
# Set key permissions (Mac/Linux)
chmod 400 ~/Downloads/price-updater-key.pem

# Connect via SSH
ssh -i ~/Downloads/price-updater-key.pem ubuntu@YOUR_EC2_IP
```

**OR use browser:** EC2 Console → Connect → EC2 Instance Connect

### Step 4: Setup Environment (10 min)

```bash
# Download and run setup script
wget https://raw.githubusercontent.com/subhan-17h/qemat_price_updaters/main/setup_aws.sh
chmod +x setup_aws.sh
./setup_aws.sh

# Clone your repository
cd ~/price_updaters
git clone https://github.com/subhan-17h/qemat_price_updaters.git .

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 5: Upload Your Files (3 min)

**From your LOCAL machine:**
```bash
# Upload .env file
scp -i ~/Downloads/price-updater-key.pem /home/rowdy/price_updaters/.env ubuntu@YOUR_EC2_IP:~/price_updaters/

# Upload input CSV
scp -i ~/Downloads/price-updater-key.pem /home/rowdy/price_updaters/test_with_matched.csv ubuntu@YOUR_EC2_IP:~/price_updaters/
```

**OR create .env manually on EC2:**
```bash
cd ~/price_updaters
nano .env
# Paste your Firebase credentials
# Ctrl+X, Y, Enter to save
```

### Step 6: Run Application (1 min)

```bash
# On EC2 instance
cd ~/price_updaters
chmod +x run_in_background.sh
./run_in_background.sh
```

✅ **Done! Your app is now running!**

---

## 📊 Monitor Progress

```bash
# SSH back anytime
ssh -i ~/Downloads/price-updater-key.pem ubuntu@YOUR_EC2_IP

# View logs in real-time
tail -f ~/price_updaters/logs/orchestrator_*.log

# Check if running
ps aux | grep python

# Check resource usage
free -h    # Memory
df -h      # Disk space
top        # CPU
```

---

## 💾 Download Results (After 3 Days)

```bash
# From your LOCAL machine:
scp -i ~/Downloads/price-updater-key.pem ubuntu@YOUR_EC2_IP:~/price_updaters/consolidated.csv .
scp -i ~/Downloads/price-updater-key.pem -r ubuntu@YOUR_EC2_IP:~/price_updaters/reports .
```

---

## 🛑 Stop & Clean Up

### Option 1: Stop Instance (Keeps your work)
```
AWS Console → EC2 → Select instance → Instance State → Stop
Cost: ~$2/month for storage only
```

### Option 2: Terminate Instance (Deletes everything)
```
AWS Console → EC2 → Select instance → Instance State → Terminate
Cost: $0 (complete cleanup)
```

⚠️ **Download results before terminating!**

---

## 💰 Cost Summary

| Period | Status | Cost |
|--------|--------|------|
| **First 12 months** | Free Tier | **$0** ✅ |
| **After 12 months** | Standard pricing | ~$8.50/month |
| **Your 3-day run** | Free Tier | **$0** ✅ |

---

## ⚠️ Important Notes

### Memory Limitations
- **t2.micro has 1 GB RAM** - may be tight for 5 stores
- **Solution if needed**: Add swap space or upgrade to t2.small ($1.70 for 3 days)

```bash
# Add 2GB swap space if needed
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### Keep Instance Running
- ✅ **EC2 keeps running** even if you disconnect SSH
- ✅ **Process continues** in background
- ✅ **No timeout limits**

### Security
- ✅ Keep your `.pem` key file secure
- ✅ Don't share your Public IP
- ✅ Delete `.env` from EC2 after completion

---

## 🆘 Common Issues

### Out of Memory
```bash
# Add swap space (see above)
# Or upgrade to t2.small: EC2 Console → Stop → Change Instance Type
```

### Can't Connect
```bash
# Check security group allows SSH from your IP
# AWS Console → EC2 → Security Groups → Edit inbound rules
```

### Process Died
```bash
# Check logs
tail -100 ~/price_updaters/logs/orchestrator_*.log

# Common causes: Out of memory, network timeout, disk full
```

### Firefox Crashes
```bash
sudo apt-get install --reinstall firefox-esr xvfb
pkill Xvfb
Xvfb :99 -screen 0 1920x1080x24 &
export DISPLAY=:99
```

---

## 📚 Full Documentation

For detailed information, see **`AWS_DEPLOYMENT.md`**

---

## ✅ Quick Commands Reference

```bash
# Connect
ssh -i ~/Downloads/price-updater-key.pem ubuntu@YOUR_EC2_IP

# View logs
tail -f ~/price_updaters/logs/orchestrator_*.log

# Check status
ps aux | grep python

# Stop process
kill $(cat ~/price_updaters/price_updater.pid)

# Download results
scp -i ~/Downloads/price-updater-key.pem ubuntu@YOUR_EC2_IP:~/price_updaters/consolidated.csv .
```

---

## 🎯 Next Steps

1. ✅ **Sign up** for AWS: https://aws.amazon.com/free
2. ✅ **Follow** the setup steps above
3. ✅ **Monitor** logs regularly
4. ✅ **Download** results after 3 days
5. ✅ **Terminate** instance to avoid future charges

---

## 📞 Need Help?

- **Full Guide**: Read `AWS_DEPLOYMENT.md`
- **AWS Docs**: https://docs.aws.amazon.com/ec2
- **Free Tier FAQ**: https://aws.amazon.com/free/free-tier-faqs

---

**🎉 Your Price Updater will run FREE on AWS for 3 days! 🚀**
