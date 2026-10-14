import urllib.request, re

url = 'https://vortexscans.org/series/the-genius-wants-to-be-ordinary/chapter-78'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        html = resp.read().decode('utf-8', errors='ignore')
        matches = re.findall(r'https://storage\.vortexscans\.org/upload/series/[^"\'\s]+page-[^"\'\s]+\.webp', html)
        print('Matches found on website:', len(matches))
        if matches:
            print('Sample:', matches[0])
except Exception as e:
    print('Failed:', e)
