from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

analyzer = SentimentIntensityAnalyzer()

def detect_sentiment(text):

    score = analyzer.polarity_scores(text)

    if score["compound"] <= -0.5:
        return "negative"

    elif score["compound"] >= 0.5:
        return "positive"

    return "neutral"