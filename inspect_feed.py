import feedparser

feed_url = "https://nexxtpress.de/author/mediathekperlen/feed/"
feed = feedparser.parse(feed_url)

print(f"Feed Title: {feed.feed.title}")
for entry in feed.entries[:3]:
    print(f"Entry Title: {entry.title}")
    # print(f"Entry Summary: {entry.summary}") 
