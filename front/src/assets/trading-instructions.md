# Pilot Design

1. Algorithm acting as a noise trader
2. Human subject has to execute an order that is either to buy # shares or to sell # shares.
3. Then we change the level of information i.e. the size of the order to execute with respect to the market volume. We use low and high information (to determine what it is).

## Treatments

| #   | Informed player | Type of order to execute | Level of information |
| --- | --------------- | ------------------------ | -------------------- |
| 5   | human           | Buy                      | Low                  |
| 6   | human           | Buy                      | High                 |
| 7   | human           | Sell                     | Low                  |
| 8   | human           | Sell                     | High                 |

## Instructions to Include in the Software

### Page 1: Welcome

**Welcome to this study!**

In this study we investigate decision-making in financial markets. The following are the instructions for this study. Please follow them carefully. You can earn considerable money depending on your decisions which we will transfer to your bank account the next working day.

In this study you will participate in markets where you can earn money by trading with other participants on our trading platform. Each market will last # minutes and you will participate in # markets.

After each market all your remaining shares and money are converted to pounds sterling which you earn from that market. Then a new market starts. You cannot use your earnings from the previous market to trade in the following markets.

In the following you will learn more about the trading platform and how to trade.

### Page 2: Trading Platform

The trading platform is software that allows you to trade with other participants. It shows relevant information about the demand and supply of an asset (e.g. a share). What you see on the trading platform is common knowledge i.e. all other participants can see it.

You can buy or sell shares. To do that you place an order. We call a buy order a "bid" and a sell order an "ask". There are two types of orders you can place:

- You can directly accept an existing price to sell or buy such as an order from another participant. In this case the trade is immediately executed at the best bid or ask respectively.
- You can place passive orders i.e. orders to sell or buy that are not immediately executed. It means that you have to wait for someone who will accept them.

You can improve the existing orders by:

- Placing an order to sell (ask) a share for a lower price than the current best ask (selling price)
- Placing an order to buy (bid) a share for a higher price than the current best bid (buying price)

You can also place orders that do not improve the best current order. For example if there is already an order to buy a share for 10 you can place an additional order to buy a share at 9.

_[Add a screenshot with arrows and a bubble to show where one can see the current prices and how to place a bid or ask.]_

### Page 3: Setup

We are going to conduct # markets in which you will be a participant. You have a straightforward task. The task is to sell all your shares OR buy a given number. At the beginning of each market we will tell you to sell OR buy a given number of shares. You can only buy OR sell shares not both.

Your objective is to sell at the highest price or buy at the lowest price. To buy or sell you will receive shares AND money at the beginning of each market.

All trading will be in terms of Liras and the length of each market will be # minutes.

### Page 4: Your Earnings (Selling)

If you do not achieve the objective within the time limit of the market the trading platform will automatically execute the following additional trades:

- If your task is to sell # shares: At the end of the market the trading platform will automatically sell each unsold share (if any) at a price equal to half of the average best bid and ask price (mid-price) at the end of each market. Loosely speaking half of the market price at the end of the market.
  - Market earnings = revenue from sales (incl. automatically sold shares) – (Number of shares) \* (mid-price at the beginning of the market)
  - The market price might drop below the mid-price at the beginning of the market. If that happens each sale of a share will make a loss. However selling the shares is still in your interest as keeping them would create an even more significant loss. To cover your losses you will given # Liras at the beginning of each market.

### Page 5: Your Earnings (Buying)

- If your task is to buy # shares: At the end of the market the trading platform will automatically buy each unpurchased share (if any) at a price equal to one and a half (1.5) of the average best bid and ask price (mid-price) at the end of each market. Loosely speaking one and a half (1.5) of the market price at the end of the market.
  - Market earnings = (Number of shares) \* (mid-price at the beginning of the market) – total expense of purchases (incl. automatically bought shares)
  - The market price might rise above the mid-price at the beginning of the market. If that happens each purchase of a share will make a loss. However buying the shares is still in your interest as not buying them would create an even more significant loss. To cover your losses you will given # Liras at the beginning of each market.

At the end of the study you will be awarded the average of your earnings across all markets (excluding the practice market); a market with negative earnings counts as zero in the average. Your average earnings are converted into GBP and paid to you. The conversion rate is X Liras = 1 GBP.

### Page 6: Other Participants in the Market

The other participants in the market are all artificial (algorithmic) traders i.e. non-human. All artificial traders have no objective in terms of earnings. These artificial traders randomly join the market for a short period to buy and sell and are then replaced by other artificial traders. These traders ensure activity in the market that enables you to buy and sell.

After answering some control questions you will practice trading to familiarise yourself with the trading platform.

### Page 7: Control Questions

1. You can both buy and sell shares. (Correct/Incorrect)
2. You must always improve an existing bid (buy order) or ask (sell order). (Correct/Incorrect)
3. All other traders are artificial? (Correct/Incorrect)
4. Do the shares you own at the end of the market pay a dividend? (Correct/Incorrect)
5. Your task is either to sell or buy shares. To maximise your earnings you must complete the task. (Correct/Incorrect)
6. Your earnings are the sum of the earnings in all markets. (correct/incorrect)

Consider a market in which you had the task of selling all your 10 shares and you received 50 Lira at the start. You sold all the 10 shares for an average price of 11. The price at the beginning of the market was 12. What would be your earnings in Lira at the end of this market? (40 Lira)

Consider a market in which you had the task of buying 10 shares and you received 60 Lira at the start. You bought 10 shares for an average price of 11. The price at the beginning of the market was 10. What would be your earnings in Lira at the end of this market? (50 Lira)

### Page 8: Practice

Now you will practice the trading platform for 5 minutes.

When you place a passive order (bid or ask) you cannot cancel it for # seconds. After # seconds have passed you can cancel it (if you want).

Each order is for one share only and you can choose the price. If you want to place an order for a quantity of X shares at price P you need to place X orders at price P.
