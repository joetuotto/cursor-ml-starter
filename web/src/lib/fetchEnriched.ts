// Data fetching for enriched content with fallback
export interface EnrichedItem {
  id?: string;
  kicker: string;
  title: string;
  lede_title?: string;
  lede: string;
  why_it_matters?: string;
  analysis?: string;
  cta: {
    label: string;
    url: string;
  };
  published_at: string;
  source_name?: string;
  source_url?: string;
  origin_country?: string;
  category_guess?: string;
  tags?: string[];
  local_fi?: string;
  local_fi_score?: number;
  enriched_at?: string;
  model_version?: string;
}

export interface EnrichedData {
  items: EnrichedItem[];
  generated_at: string;
  summary?: string;
}

// Sample fallback data based on schema
const createFallbackData = (): EnrichedData => ({
  items: [
    {
      kicker: "Technology",
      title: "AI Models Show Promise in Market Analysis",
      lede: "Recent developments in machine learning demonstrate significant potential for financial forecasting and risk assessment across multiple sectors.",
      why_it_matters: "This breakthrough could transform how financial institutions approach predictive modeling and risk management.",
      cta: {
        label: "Read analysis",
        url: "#"
      },
      published_at: new Date(Date.now() - 1000 * 60 * 15).toISOString() // 15 minutes ago
    },
    {
      kicker: "Markets", 
      title: "Global Supply Chain Resilience Metrics",
      lede: "New indicators suggest strengthening supply chain networks as international trade patterns stabilize following recent disruptions.",
      why_it_matters: "Supply chain stability directly impacts inflation rates and consumer pricing across key economic sectors.",
      cta: {
        label: "View metrics",
        url: "#"
      },
      published_at: new Date(Date.now() - 1000 * 60 * 45).toISOString() // 45 minutes ago
    },
    {
      kicker: "Energy",
      title: "Renewable Infrastructure Investment Patterns",
      lede: "Analysis reveals shifting investment flows toward sustainable energy projects, with particular emphasis on grid modernization initiatives.",
      cta: {
        label: "Explore data",
        url: "#"
      },
      published_at: new Date(Date.now() - 1000 * 60 * 90).toISOString() // 90 minutes ago
    },
    {
      kicker: "Economic Indicators",
      title: "Regional Employment Trend Analysis",
      lede: "Labor market data shows varied regional recovery patterns with emerging clusters of high-skill job creation in technology corridors.",
      why_it_matters: "Employment distribution affects regional economic development and migration patterns.",
      cta: {
        label: "See trends",
        url: "#"
      },
      published_at: new Date(Date.now() - 1000 * 60 * 120).toISOString() // 2 hours ago
    },
    {
      kicker: "Finance",
      title: "Interest Rate Impact on Housing Markets",
      lede: "Mortgage rate fluctuations create complex ripple effects across regional housing markets, with notable variations in price elasticity.",
      cta: {
        label: "Read more",
        url: "#"
      },
      published_at: new Date(Date.now() - 1000 * 60 * 180).toISOString() // 3 hours ago
    },
    {
      kicker: "Trade",
      title: "Import-Export Balance Indicators",
      lede: "Trade balance metrics reveal evolving patterns in international commerce, particularly in manufactured goods and raw materials.",
      why_it_matters: "Trade balances influence currency stability and domestic manufacturing competitiveness.",
      cta: {
        label: "View analysis",
        url: "#"
      },
      published_at: new Date(Date.now() - 1000 * 60 * 240).toISOString() // 4 hours ago
    },
    {
      kicker: "Banking",
      title: "Digital Payment System Evolution",
      lede: "Financial technology adoption accelerates as digital payment infrastructures demonstrate increased reliability and security measures.",
      cta: {
        label: "Learn more",
        url: "#"
      },
      published_at: new Date(Date.now() - 1000 * 60 * 300).toISOString() // 5 hours ago
    },
    {
      kicker: "Regulation",
      title: "Financial Compliance Framework Updates",
      lede: "Regulatory developments address emerging challenges in digital asset management and cross-border transaction monitoring.",
      why_it_matters: "Updated compliance frameworks affect institutional investment strategies and risk assessment procedures.",
      cta: {
        label: "Read details",
        url: "#"
      },
      published_at: new Date(Date.now() - 1000 * 60 * 360).toISOString() // 6 hours ago
    },
    {
      kicker: "Innovation",
      title: "Fintech Collaboration Networks",
      lede: "Strategic partnerships between traditional financial institutions and technology companies create new service delivery models.",
      cta: {
        label: "Explore partnerships",
        url: "#"
      },
      published_at: new Date(Date.now() - 1000 * 60 * 420).toISOString() // 7 hours ago
    },
    {
      kicker: "Research",
      title: "Behavioral Economics in Investment Decisions",
      lede: "Studies reveal cognitive biases significantly influence individual and institutional investment patterns, with implications for market efficiency.",
      why_it_matters: "Understanding behavioral factors helps improve risk assessment models and investment strategy development.",
      cta: {
        label: "View research",
        url: "#"
      },
      published_at: new Date(Date.now() - 1000 * 60 * 480).toISOString() // 8 hours ago
    }
  ],
  generated_at: new Date().toISOString(),
  summary: "Financial and economic analysis covering market trends, technology adoption, and regulatory developments."
});

// Format time ago
export const formatTimeAgo = (dateString: string): string => {
  const now = new Date();
  const date = new Date(dateString);
  const diffMs = now.getTime() - date.getTime();
  const diffMinutes = Math.floor(diffMs / (1000 * 60));
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffMinutes < 1) return 'just now';
  if (diffMinutes < 60) return `${diffMinutes}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  
  // Fallback to formatted date
  return date.toLocaleDateString();
};

// Clip text to specified length
export const clipText = (text: string, maxLength: number): string => {
  if (!text) return '';
  if (text.length <= maxLength) return text;
  
  // Find last space before maxLength to avoid cutting words
  const clipped = text.slice(0, maxLength);
  const lastSpace = clipped.lastIndexOf(' ');
  const result = lastSpace > 0 ? clipped.slice(0, lastSpace) : clipped;
  
  return result + '…';
};

// Fetch enriched data with fallback
export const fetchEnrichedData = async (): Promise<EnrichedData> => {
  try {
    // Try to fetch from static artifacts first
    const response = await fetch('/artifacts/report.enriched.json');
    
    if (response.ok) {
      const data = await response.json();
      
      // Validate data structure
      if (data && Array.isArray(data.items) && data.items.length > 0) {
        return data;
      }
    }
    
    // If artifacts fetch fails, try API endpoint
    console.log('Artifacts not found, trying API schema endpoint...');
    const schemaResponse = await fetch('/schemas/feed_item.json');
    
    if (schemaResponse.ok) {
      console.log('Schema endpoint available, using fallback data');
      return createFallbackData();
    }
    
    // If both fail, return fallback anyway
    console.log('API schema not available, using fallback data');
    return createFallbackData();
    
  } catch (error) {
    console.warn('Error fetching enriched data, using fallback:', error);
    return createFallbackData();
  }
};

// Sort items by published date (newest first)
export const sortByPublishedDate = (items: EnrichedItem[]): EnrichedItem[] => {
  return [...items].sort((a, b) => {
    const dateA = new Date(a.published_at);
    const dateB = new Date(b.published_at);
    return dateB.getTime() - dateA.getTime();
  });
};
