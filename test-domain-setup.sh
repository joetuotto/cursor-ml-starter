#!/bin/bash

# Domain setup verification script for paranoidmodels.com
# Run this after adding DNS records to Google Domains

DOMAIN="paranoidmodels.com"
API_DOMAIN="api.paranoidmodels.com"

echo "🔍 Testing DNS setup for $DOMAIN..."
echo "============================================"

# Test DNS resolution
echo "📡 DNS A records:"
dig +short A $DOMAIN
echo

echo "📡 DNS AAAA records:"  
dig +short AAAA $DOMAIN
echo

# Check if we get the expected Google Cloud IPs
EXPECTED_IPS=("216.239.32.21" "216.239.34.21" "216.239.36.21" "216.239.38.21")
ACTUAL_IPS=($(dig +short A $DOMAIN))

echo "✅ Expected IPs: ${EXPECTED_IPS[*]}"
echo "📊 Actual IPs:   ${ACTUAL_IPS[*]}"

if [ ${#ACTUAL_IPS[@]} -eq 0 ]; then
    echo "❌ No A records found. DNS not configured yet."
    exit 1
fi

# Test HTTP connectivity (might fail due to SSL provisioning)
echo
echo "🌐 Testing HTTP connectivity..."
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://$DOMAIN/health 2>/dev/null || echo "000")
echo "HTTP status: $HTTP_STATUS"

# Test HTTPS connectivity  
echo "🔒 Testing HTTPS connectivity..."
HTTPS_STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://$DOMAIN/health 2>/dev/null || echo "000")
echo "HTTPS status: $HTTPS_STATUS"

if [ "$HTTPS_STATUS" = "200" ]; then
    echo "🎉 SUCCESS! Domain is fully configured!"
    echo "🔗 API endpoint: https://$DOMAIN/health"
    curl -s https://$DOMAIN/health | jq .
elif [ "$HTTP_STATUS" = "200" ]; then
    echo "⏳ HTTP works, HTTPS SSL certificate still provisioning..."
    echo "💡 Try again in 15-30 minutes"
elif [ ${#ACTUAL_IPS[@]} -gt 0 ]; then
    echo "⏳ DNS configured, but HTTP/HTTPS not responding yet"
    echo "💡 SSL certificate might still be provisioning (up to 24h)"
else
    echo "❌ DNS not configured properly"
fi

echo
echo "📊 Domain mapping status:"
gcloud beta run domain-mappings list --region europe-north1 2>/dev/null || echo "❌ gcloud not configured"

echo
echo "🔍 Comparison test (API subdomain should work):"
API_STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://$API_DOMAIN/health 2>/dev/null || echo "000")
echo "API subdomain status: $API_STATUS"
