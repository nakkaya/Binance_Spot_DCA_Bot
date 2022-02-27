import config,os
try:
    import ccxt
except:
    os.system("pip install ccxt")
try:
    import pandas as pd
except:
    os.system("pip install pandas")
from smtplib import SMTP

# SETTİNGS
symbolName = input("Symbol (BTC, ETH, LTC...): ").upper()
baseOrderSize = float(input("Base Order Size: "))
safetyOrderSize = float(input("Safety Order Size: "))
maxSafetyTradesCount = float(input("Max Safety Trades Count: "))
priceDeviation = float(input("Price Deviation %: "))
safetyOrderStepScale = float(input("Safety Order Step Scale: "))
safetyOrderVolumeScale = float(input("Safety Order Volume Scale: "))
takeProfitType = float(input("Take Profit Type (Classic TP(1) - Trailing TP(2)): "))
if takeProfitType == 1:
    takeProfit = float(input("Take Profit %: "))
if takeProfitType == 2:
    takeProfitTrigger = float(input("Trailing Take Profit Trigger %: "))
    takeProfitTrailing = float(input("Trailing Take Profit %: "))
SLselection = float(input("Do you want stop loss? = YES(1) - NO(2): "))
if SLselection == 1:
    stopLossType = float(input("Stop Loss Type = Classic SL(1) - Trailing SL(2): "))
    if stopLossType == 1:
        stopLoss = float(input("Stop Loss %: "))
    if stopLossType == 2:
        stopLossTrailing = float(input("Trailing Stop Loss %: "))
profitAmount = float(input("Profit Amount: "))
mail = float(input("Bot Send e-mail? (YES(1) - NO(2)): "))

#ATTRIBUTES
first = True
longTPtrigger = False
inPosition = False
tradeCount = 0
symbol = symbolName+"/USDT"
mainSafetyOrderSize = safetyOrderSize
mainPriceDeviation = priceDeviation
prices = []
amounts = []
takeProfitCount = 0
highestPrice = 0
lowestPrice = 0

# API CONNECT
exchange = ccxt.binance({
"apiKey": config.apiKey,
"secret": config.secretKey,

'options': {
'defaultType': 'spot'
},
'enableRateLimit': True
})

while True:
    try:
        
        balance = exchange.fetch_balance()
        
        # LOAD BARS
        bars = exchange.fetch_ohlcv(symbol, timeframe="1m", since = None, limit = 1)
        df = pd.DataFrame(bars, columns=["timestamp", "open", "high", "low", "close", "volume"])

        # in position?
        if float(balance["total"][symbolName]) * float(df["close"][len(df.index) - 1]) >= 10:
            inPosition = True
        else: inPosition = False

        totalMoney = float(balance["total"]["USDT"])
        currentPrice = float(df["close"][len(df.index) - 1])

        # Starting price
        if first:
            firstPrice = float(df["close"][len(df.index) - 1])
            highestPrice = currentPrice
            lowestPrice = currentPrice
            first = False
        
        # LONG ENTER
        def longEnter(alinacak_miktar):
            order = exchange.create_market_buy_order(symbol, alinacak_miktar)
            prices.append(float(order["price"]))
            amounts.append(float(order["amount"]))
 
        # LONG EXIT
        def longExit():
            order = exchange.create_market_sell_order(symbol, float(balance["total"][symbolName]))
            prices.clear()
            amounts.clear()

        if inPosition == False:
            priceDeviation = mainPriceDeviation
            safetyOrderSize = mainSafetyOrderSize
        
        # LONG ENTER
        if firstPrice - (firstPrice/100) * priceDeviation >= currentPrice and maxSafetyTradesCount>tradeCount:
            if tradeCount == 0:
                alinacak_miktar = (baseOrderSize) / float(df["close"][len(df.index) - 1])
            if tradeCount > 0:
                alinacak_miktar = (safetyOrderSize) / float(df["close"][len(df.index) - 1])
                safetyOrderSize = safetyOrderSize*safetyOrderVolumeScale
            priceDeviation = priceDeviation * safetyOrderStepScale
            longEnter(alinacak_miktar)
            print("BUY ORDER")
            first = True
            tradeCount = tradeCount + 1
            if tradeCount >= maxSafetyTradesCount:
                lastOrderPrice = float(prices[len(prices)-1])
            if mail == 1:
                baslik = symbol
                message = "BUY ORDER\n" + "TOTAL USDT: " + str(totalMoney)
                content = f"Subject: {baslik}\n\n{message}"
                mail = SMTP("smtp.gmail.com", 587)
                mail.ehlo()
                mail.starttls()
                mail.login(config.mailAddress, config.password)
                mail.sendmail(config.mailAddress, config.mailAddress, content.encode("utf-8"))
        
        #average price
        if prices:
            y=0
            a=0
            for price in prices:
                for amount in amounts:
                    y=y+price*amount
                    a = a+amount
            averagePrice = y/a

        # TAKE PROFIT - CLASSIC
        if takeProfitType == 1 and inPosition and ((averagePrice/100)*takeProfit)+averagePrice < currentPrice:
            print("TAKE PROFIT")
            longExit()
            if mail == 1:
                baslik = symbol
                message = "TAKE PROFIT\n" + "TOTAL USDT: " + str(totalMoney)
                content = f"Subject: {baslik}\n\n{message}"
                mail = SMTP("smtp.gmail.com", 587)
                mail.ehlo()
                mail.starttls()
                mail.login(config.mailAddress, config.password)
                mail.sendmail(config.mailAddress, config.mailAddress, content.encode("utf-8"))
            first = True
            tradeCount = 0
            takeProfitCount = takeProfitCount+ 1
        
        # get highest price
        if currentPrice > highestPrice:
            highestPrice = currentPrice
        else: highestPrice = highestPrice

        # LONG TAKE PROFIT - TRAILING TRIGGER
        if takeProfitType == 2 and inPosition and ((averagePrice/100)*takeProfitTrigger)+averagePrice <= currentPrice:
            longTPtrigger = True

        # TAKE PROFIT - TRAILING
        if takeProfitType == 2 and longTPtrigger and inPosition and highestPrice - (highestPrice/100) * takeProfitTrailing >= currentPrice:
            print("TRAILING TAKE PROFIT")
            longExit()
            longTPtrigger = False
            first = True
            tradeCount = 0
            if mail == 1:
                baslik = symbol
                message = "LONG TRAILING TAKE PROFIT\n" + "TOTAL USDT: " + str(balance['total']["USDT"])
                content = f"Subject: {baslik}\n\n{message}"
                mail = SMTP("smtp.gmail.com", 587)
                mail.ehlo()
                mail.starttls()
                mail.login(config.mailAddress, config.password)
                mail.sendmail(config.mailAddress, config.mailAddress, content.encode("utf-8"))
            takeProfitCount = takeProfitCount+ 1
            
            
        # STOP LOSS - CLASSIC
        if SLselection == 1 and stopLossType == 1 and inPosition and maxSafetyTradesCount<=tradeCount and firstPrice - (firstPrice/100) * stopLoss >= currentPrice:
            print("STOP LOSS")
            longExit()
            longTPtrigger = False
            if mail == 1:
                baslik = symbol
                message = "STOP LOSS\n" + "TOTAL USDT: " + str(totalMoney)
                content = f"Subject: {baslik}\n\n{message}"
                mail = SMTP("smtp.gmail.com", 587)
                mail.ehlo()
                mail.starttls()
                mail.login(config.mailAddress, config.password)
                mail.sendmail(config.mailAddress, config.mailAddress, content.encode("utf-8"))
            first = True
            tradeCount = 0

        # STOP LOSS - TRAILING
        if SLselection == 1 and stopLossType == 2 and inPosition and maxSafetyTradesCount<=tradeCount and highestPrice - (highestPrice/100) * stopLossTrailing >= currentPrice:
            print("TRAILING STOP LOSS")
            longExit()
            longTPtrigger = False
            first = True
            tradeCount = 0
            if mail == 1:
                baslik = symbol
                message = "LONG TRAILING STOP LOSS\n" + "TOTAL USDT: " + str(balance['total']["USDT"])
                content = f"Subject: {baslik}\n\n{message}"
                mail = SMTP("smtp.gmail.com", 587)
                mail.ehlo()
                mail.starttls()
                mail.login(config.mailAddress, config.password)
                mail.sendmail(config.mailAddress, config.mailAddress, content.encode("utf-8"))

        if takeProfitCount == profitAmount:
            exit()

        print("========== SETTINGS ========== ")
        print("Pair: ", symbol)
        print("Base Order Size: ", baseOrderSize, " Safety Order Size: ", safetyOrderSize)
        print("Max Safety Trades Count: ", maxSafetyTradesCount, " Price Deviation: %"+str(priceDeviation))
        print("Safety Order Step Scale: ", safetyOrderStepScale, " Safety Order Volume Scale: ", safetyOrderVolumeScale)
        if takeProfitType == 1:
            print("Take Profit Type Is Classic. Take Profit: %"+str(takeProfit))
        if takeProfitType == 2:
            print("Take Profit Type Is Trailing. Trigger: %"+str(takeProfitTrigger), " Take Profit: %"+str(takeProfitTrailing))
        if SLselection == 2:
            print("No Stop Loss")
        if SLselection == 1:
            if stopLossType == 1:
                print("Stop Loss Type Is Classic. Stop Loss: %"+str(stopLoss))
            if stopLossType == 2:
                print("Stop Loss Type Is Trailing. Stop Loss: %"+str(stopLossTrailing))
        print("After triggering take profit",profitAmount - takeProfitCount,", the bot will stop working")
        print("========== INFORMATIONS ========== ")
        if inPosition:
            print("In Position")
        if inPosition:
            print("Trade Count: ", tradeCount, " Avarege Price: ", averagePrice, " Current Price: ", currentPrice, " Total USDT: ", round(totalMoney,2))
        if inPosition == False: 
            print("Starting Price: ", firstPrice, " Current Price: ", currentPrice, " Total USDT: ", round(totalMoney,2))
        print("=======================================================================================================================================")

    except ccxt.BaseError as Error:
        print ("[ERROR] ", Error )
        continue
