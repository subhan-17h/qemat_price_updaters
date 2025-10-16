# 🚀 AWS Free Tier Deployment Guide - Price Updater

Complete guide for deploying your Price Updater on AWS EC2 Free Tier for 3-day continuous operation.

---

## 📋 Table of Contents
- [Why AWS Free Tier?](#why-aws-free-tier)
- [AWS Free Tier Limits](#aws-free-tier-limits)
- [Prerequisites](#prerequisites)
- [Step-by-Step Setup](#step-by-step-setup)
- [Running the Application](#running-the-application)
- [Monitoring](#monitoring)
- [Cost Management](#cost-management)
- [Troubleshooting](#troubleshooting)

---

## Why AWS Free Tier?

**Perfect for this project because:**
- ✅ **750 hours/month free** for 12 months (enough for continuous 3-day run)
- ✅ **t2.micro/t3.micro instance** (1 vCPU, 1GB RAM)
- ✅ **30 GB storage free**
- ✅ **No timeout limits** - runs as long as you need
- ✅ **Reliable and well-documented**
- ✅ **Works great with Firebase**

**Limitations to note:**
- ⚠️ **1 GB RAM** - may be tight for 5 simultaneous stores
- ⚠️ **1 vCPU** - slower than paid options but works
- ⚠️ **12 months only** - after that, you'll be charged (~$8.50/month)

---

## AWS Free Tier Limits

### What's Included (12 Months):

| Resource | Free Tier Limit | Your Usage |
|----------|----------------|------------|
| **EC2 Instance** | 750 hours/month (t2.micro) | ~72 hours (3 days) ✅ |
| **Storage** | 30 GB EBS | ~20 GB ✅ |
| **Data Transfer** | 15 GB out/month | ~1-2 GB ✅ |

**Your 3-day run will cost: $0 (within free tier)** 🎉

---

## Prerequisites

1. **AWS Account**
   - Sign up at: https://aws.amazon.com/free
   - Requires credit card (won't charge within free tier)
   - Free tier valid for 12 months

2. **Your Files Ready**
   - `.env` file (Firebase credentials) 
   - `test_with_matched.csv` (input data)
   - Your project code

3. **Basic Terminal Knowledge**
   - You'll use SSH to connect to EC2

---

## Step-by-Step Setup

### Part 1: Create AWS Account

1. **Sign up for AWS**
   ```
   → Go to: https://aws.amazon.com/free
   → Click "Create a Free Account"
   → Complete signup (credit card required for verification)
   → Activate Free Tier (12 months)
   ```

2. **Sign in to AWS Console**
   ```
   → Go to: https://console.aws.amazon.com
   → Sign in with your new account
   ```

### Part 2: Launch EC2 Instance

1. **Navigate to EC2**
   ```
   → In AWS Console, search for "EC2"
   → Click "EC2" to open dashboard
   → Select your region (e.g., us-east-1 - cheapest)
   ```

2. **Launch Instance**
   ```
   → Click "Launch Instance" (orange button)
   
   Configure:
   ┌─────────────────────────────────────────────┐
   │ Name: price-updater                         │
   │                                             │
   │ Application and OS Images:                  │
   │ → Ubuntu Server 22.04 LTS (Free tier)      │
   │                                             │
   │ Instance type:                              │
   │ → t2.micro (1 vCPU, 1 GB RAM)             │
   │   ✅ Free tier eligible                     │
   │                                             │
   │ Key pair (login):                           │
   │ → Click "Create new key pair"               │
   │   Name: price-updater-key                   │
   │   Type: RSA                                 │
   │   Format: .pem (for SSH)                    │
   │   Download and save it securely!            │
   │                                             │
   │ Network settings:                           │
   │ → ☑ Allow SSH traffic from: My IP          │
   │   (This restricts access to your IP only)   │
   │                                             │
   │ Configure storage:                          │
   │ → 20 GB gp3 (Free tier: up to 30 GB)      │
   └─────────────────────────────────────────────┘
   
   → Click "Launch Instance"
   → Wait 1-2 minutes for instance to start
   ```

3. **Note Your Instance Details**
   ```
   → Click "View Instances"
   → Find your "price-updater" instance
   → Note the "Public IPv4 address" (e.g., 3.80.123.45)
   ```

### Part 3: Connect to Your EC2 Instance

**Option 1: Using SSH (Mac/Linux)**

```bash
# Set permissions on your key file
chmod 400 ~/Downloads/price-updater-key.pem

# Connect to your instance
ssh -i ~/Downloads/price-updater-key.pem ubuntu@YOUR_EC2_PUBLIC_IP

# Example:
# ssh -i ~/Downloads/price-updater-key.pem ubuntu@3.80.123.45
```

**Option 2: Using EC2 Instance Connect (Browser)**

```
→ In EC2 Console, select your instance
→ Click "Connect" button
→ Choose "EC2 Instance Connect" tab
→ Click "Connect" (opens browser terminal)
```

### Part 4: Setup the Instance

1. **Run Setup Script**

```bash
# Download the setup script
wget https://raw.githubusercontent.com/subhan-17h/qemat_price_updaters/main/setup_aws.sh

# Make it executable
chmod +x setup_aws.sh

# Run the setup
./setup_aws.sh
```

2. **Clone Your Repository**

```bash
cd ~/price_updaters
git clone https://github.com/subhan-17h/qemat_price_updaters.git .
```

### Part 5: Upload Your Files

**Method 1: Using SCP (Mac/Linux)**

```bash
# From your LOCAL machine:
scp -i ~/Downloads/price-updater-key.pem /home/rowdy/price_updaters/.env ubuntu@YOUR_EC2_IP:~/price_updaters/
scp -i ~/Downloads/price-updater-key.pem /home/rowdy/price_updaters/test_with_matched.csv ubuntu@YOUR_EC2_IP:~/price_updaters/
```

**Method 2: Create .env Manually on EC2**

```bash
# On the EC2 instance:
cd ~/price_updaters
nano .env

# Paste your Firebase credentials
# Press Ctrl+X, then Y, then Enter to save
```

**Method 3: Use GitHub (if you have a private repo)**

```bash
# Store .env in GitHub Secrets and fetch it
# Or use AWS Secrets Manager (more advanced)
```

### Part 6: Install Dependencies and Run

```bash
# On your EC2 instance:
cd ~/price_updaters

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Make run script executable
chmod +x run_in_background.sh

# Start the application
./run_in_background.sh
```

---

## Running the Application

### Test Run First

```bash
# Activate environment
source ~/price_updaters/venv/bin/activate
cd ~/price_updaters

# Test with step1-only
python3 orchestrator.py test_with_matched.csv --step1-only
```

### Full Production Run (3 Days)

```bash
# Make sure you're in the right directory
cd ~/price_updaters

# Start the background process
./run_in_background.sh

# The script will:
# ✅ Start virtual display (Xvfb)
# ✅ Run orchestrator in background
# ✅ Create detailed logs
# ✅ Continue even if SSH disconnects
```

---

## Monitoring

### View Logs in Real-Time

```bash
# SSH back into your instance
ssh -i ~/Downloads/price-updater-key.pem ubuntu@YOUR_EC2_IP

# View logs
cd ~/price_updaters
tail -f logs/orchestrator_*.log
```

### Check Process Status

```bash
# Check if running
ps aux | grep python

# Check process ID
cat price_updater.pid

# Check memory usage
free -h

# Check disk space
df -h
```

### Stop the Process

```bash
# Stop using PID file
kill $(cat ~/price_updaters/price_updater.pid)

# Or find and kill manually
ps aux | grep orchestrator
kill <PID>
```

---

## Cost Management

### Free Tier Usage (First 12 Months)

| Item | Free Tier | Your Usage | Cost |
|------|-----------|------------|------|
| **t2.micro instance** | 750 hrs/month | 72 hours (3 days) | **$0** |
| **20 GB storage** | 30 GB free | 20 GB | **$0** |
| **Data transfer** | 15 GB out/month | ~1-2 GB | **$0** |

**Total Cost for 3-Day Run: $0** ✅

### After Free Tier (Month 13+)

| Item | Monthly Cost | 3-Day Cost |
|------|--------------|------------|
| **t2.micro instance** | ~$8.50 | ~$0.85 |
| **20 GB storage** | ~$2.00 | ~$0.20 |
| **Data transfer** | ~$0.10/GB | ~$0.20 |
| **Total** | ~$10.50/month | **~$1.25** |

### Cost-Saving Tips

1. **Stop instance when not in use**
   ```bash
   # From AWS Console:
   → Select your instance
   → Instance state → Stop instance
   # You only pay for storage when stopped (~$2/month)
   ```

2. **Terminate instance after completion**
   ```bash
   # Download results first!
   → Instance state → Terminate instance
   # Stops all charges
   ```

3. **Set up billing alerts**
   ```
   → AWS Console → Billing Dashboard
   → Billing Preferences → Enable alerts
   → Set alert for $1 threshold
   ```

---

## Download Results

### Method 1: Using SCP (Mac/Linux)

```bash
# From your LOCAL machine:
scp -i ~/Downloads/price-updater-key.pem ubuntu@YOUR_EC2_IP:~/price_updaters/consolidated.csv .
scp -i ~/Downloads/price-updater-key.pem -r ubuntu@YOUR_EC2_IP:~/price_updaters/reports .
```

### Method 2: Using AWS S3 (Alternative)

```bash
# On EC2 instance:
# Install AWS CLI
sudo apt-get install -y awscli

# Upload to S3 bucket
aws s3 cp consolidated.csv s3://your-bucket-name/
aws s3 cp reports/ s3://your-bucket-name/reports/ --recursive

# Download from your local machine
aws s3 cp s3://your-bucket-name/consolidated.csv .
```

---

## Troubleshooting

### Out of Memory Issues

**Problem**: t2.micro only has 1 GB RAM

**Solutions**:
```bash
# 1. Add swap space
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# 2. Run stores sequentially instead of parallel
# (Edit main.py to process one store at a time)

# 3. Upgrade to t2.small (costs ~$0.023/hour = $1.70 for 3 days)
```

### Firefox Crashes

```bash
# Reinstall Firefox and dependencies
sudo apt-get update
sudo apt-get install --reinstall firefox-esr xvfb

# Restart virtual display
pkill Xvfb
Xvfb :99 -screen 0 1920x1080x24 > /dev/null 2>&1 &
export DISPLAY=:99
```

### Connection Timeout

```bash
# Check security group settings
# In AWS Console:
→ EC2 → Security Groups
→ Select your instance's security group
→ Inbound rules → Ensure SSH (port 22) is allowed from your IP
```

### Process Died

```bash
# Check logs for errors
tail -100 ~/price_updaters/logs/orchestrator_*.log

# Common causes:
# 1. Out of memory → Add swap or upgrade instance
# 2. Network issues → Check internet connectivity
# 3. Disk full → Check: df -h
```

### Can't Connect to Firebase

```bash
# Verify .env file
cat ~/price_updaters/.env

# Test Firebase connection
cd ~/price_updaters
source venv/bin/activate
python3 -c "from firebase_config import load_firebase_config_from_env; print('✅ Config OK')"
```

---

## Performance Optimization for t2.micro

### If Running Slow:

1. **Run stores sequentially** instead of all at once
2. **Increase delay between requests** (reduce load)
3. **Add swap space** (see troubleshooting)
4. **Consider upgrading** to t2.small for $1.70/3-days

### Monitoring Performance:

```bash
# CPU usage
top

# Memory usage
free -h

# Disk I/O
iostat -x 1
```

---

## Quick Reference Commands

```bash
# Connect to instance
ssh -i ~/Downloads/price-updater-key.pem ubuntu@YOUR_EC2_IP

# Start application
cd ~/price_updaters && ./run_in_background.sh

# View logs
tail -f ~/price_updaters/logs/orchestrator_*.log

# Check if running
ps aux | grep python

# Stop process
kill $(cat ~/price_updaters/price_updater.pid)

# Download results (from LOCAL machine)
scp -i ~/Downloads/price-updater-key.pem ubuntu@YOUR_EC2_IP:~/price_updaters/consolidated.csv .

# Stop instance (from AWS Console)
Instance State → Stop Instance

# Terminate instance (from AWS Console)
Instance State → Terminate Instance
```

---

## Security Best Practices

1. ✅ **Use .env file** (not serviceAccountKey.json)
2. ✅ **Restrict SSH** to your IP only
3. ✅ **Keep key file secure** (chmod 400)
4. ✅ **Delete .env from EC2** after completion
5. ✅ **Terminate instance** when done
6. ✅ **Never commit .env** to git

---

## Comparison: t2.micro vs Paid Options

| Instance | vCPU | RAM | Cost/Month | 3-Day Cost | Recommendation |
|----------|------|-----|------------|------------|----------------|
| **t2.micro** | 1 | 1 GB | Free (12mo) | **$0** | ✅ Try first |
| **t2.small** | 1 | 2 GB | $16.79 | $1.68 | If OOM errors |
| **t2.medium** | 2 | 4 GB | $33.58 | $3.36 | Best performance |

---

## What to Expect

### Timeline:
```
Hour 0:     Setup complete, scraping starts
Hour 6:     First store complete (Al-Fatah)
Hour 18:    Second store complete (Jalal Sons)
Hour 30:    Third store complete (Rainbow)
Hour 48:    Fourth store complete (Metro)
Hour 60:    Fifth store complete (Imtiaz)
Hour 72:    Firebase sync complete! ✅
```

### Success Indicators:
- ✅ Process running: `ps aux | grep python`
- ✅ Logs updating: `tail -f logs/orchestrator_*.log`
- ✅ No memory errors in logs
- ✅ CSV files being generated in `price_updates/`

---

## Need Help?

**AWS Resources:**
- Free Tier: https://aws.amazon.com/free
- EC2 Documentation: https://docs.aws.amazon.com/ec2
- Free Tier FAQ: https://aws.amazon.com/free/free-tier-faqs

**Project Issues:**
- Check logs: `tail -f logs/orchestrator_*.log`
- GitHub Issues: https://github.com/subhan-17h/qemat_price_updaters/issues

---

**🎉 You're all set! Your price updater will run for 3 days on AWS Free Tier, completely free!**
