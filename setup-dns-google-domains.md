# Squarespace DNS Setup for paranoidmodels.com
*Note: Google Domains migrated to Squarespace in 2023*

## 🎯 Quick Setup Instructions

### 1. Navigate to Squarespace Domains
- URL: https://domains.squarespace.com/
- Login with your former Google Domains credentials
- Select "paranoidmodels.com"
- Go to "DNS Settings" or "Advanced DNS"
- Click "Custom Records" section

### 2. Delete any existing A/AAAA records for @ (root domain)

### 3. Add these A records:

```
Host: @ (or leave empty for root domain)
Type: A  
TTL: 3600 (or "1 hour" from dropdown)
Value: 216.239.32.21
```

```
Subdomain: @
Type: A
TTL: 3600  
Data: 216.239.34.21
```

```
Subdomain: @
Type: A
TTL: 3600
Data: 216.239.36.21
```

```
Subdomain: @
Type: A
TTL: 3600
Data: 216.239.38.21
```

### 4. Add these AAAA records:

```
Subdomain: @
Type: AAAA
TTL: 3600
Data: 2001:4860:4802:32::15
```

```
Subdomain: @
Type: AAAA
TTL: 3600
Data: 2001:4860:4802:34::15
```

```
Subdomain: @
Type: AAAA
TTL: 3600
Data: 2001:4860:4802:36::15
```

```
Subdomain: @
Type: AAAA
TTL: 3600
Data: 2001:4860:4802:38::15
```

### 5. Optional: Add www redirect

```
Subdomain: www
Type: CNAME
TTL: 3600
Data: paranoidmodels.com
```

## ✅ Verification Commands

After adding records, run these to verify:

```bash
# Test DNS resolution
dig paranoidmodels.com

# Test A records specifically
dig A paranoidmodels.com

# Test AAAA records
dig AAAA paranoidmodels.com

# Test the API endpoint (after SSL provisions)
curl -sS https://paranoidmodels.com/health
```

## 📊 Expected Timeline

- DNS propagation: 5-15 minutes (Google Domains is fast)
- SSL certificate: 15 minutes - 24 hours  
- First successful HTTPS request: Usually within 30 minutes

## 🎯 Success Indicators

✅ `dig paranoidmodels.com` shows the Google Cloud IPs  
✅ `curl https://paranoidmodels.com/health` returns JSON response  
✅ Browser shows green lock icon at https://paranoidmodels.com  

## 🆘 Troubleshooting

If it doesn't work after 1 hour:
1. Check DNS: `dig paranoidmodels.com`
2. Verify records in Google Domains match exactly
3. Check Cloud Run domain mapping: `gcloud beta run domain-mappings list --region europe-north1`
4. Test API subdomain still works: `curl https://api.paranoidmodels.com/health`
