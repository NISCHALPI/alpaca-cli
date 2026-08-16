from typing import List


def generate_sparkline(prices: List[float]) -> str:
    """Generate 8-level ASCII Unicode sparkline trajectory for a price series."""
    if not prices:
        return ""
        
    min_p = min(prices)
    max_p = max(prices)
    rng = max_p - min_p
    
    ticks = [' ', '▂', '▃', '▄', '▅', '▆', '▇', '█']
    if rng == 0:
        return ticks[3] * min(len(prices), 8)
        
    result = []
    if len(prices) > 8:
        step = len(prices) / 8.0
        sampled = [prices[int(i * step)] for i in range(8)]
    else:
        sampled = prices
        
    for p in sampled:
        idx = int(((p - min_p) / rng) * 7)
        idx = max(0, min(7, idx))
        result.append(ticks[idx])
        
    return "".join(result)
