# Data access test

Run (UTC): 2026-11-11 16:21

## NSE static files
- EQUITY_L (nsearchives.nseindia.com): HTTP 200, 185986 bytes. rows=2634; header=`SYMBOL,NAME OF COMPANY, SERIES, DATE OF LISTING, PAID UP VALUE, MARKET LOT, ISIN NUMBER, FACE VALUE`
- EQUITY_L (archives.nseindia.com): HTTP 200, 185986 bytes. rows=2634; header=`SYMBOL,NAME OF COMPANY, SERIES, DATE OF LISTING, PAID UP VALUE, MARKET LOT, ISIN NUMBER, FACE VALUE`

## NSE daily files, last 8 calendar days
### 2026-11-11 (Wed)
- CM bhavcopy (new UDiFF): HTTP 200, 211595 bytes. rows=3775; header=`TradDt,BizDt,Sgmt,Src,FinInstrmTp,FinInstrmId,ISIN,TckrSymb,SctySrs,XpryDt,FininstrmActlXpryDt,StrkPric,OptnTp,FinInstrmNm,OpnPric,HghPric,LwPric,ClsPric,LastPr`
- sec_bhavdata_full: HTTP 200, 406680 bytes. rows=3584; header=`SYMBOL, SERIES, DATE1, PREV_CLOSE, OPEN_PRICE, HIGH_PRICE, LOW_PRICE, LAST_PRICE, CLOSE_PRICE, AVG_PRICE, TTL_TRD_QNTY, TURNOVER_LACS, NO_OF_TRADES, DELIV_QTY, `
- index close: HTTP 200, 15746 bytes. rows=147; header=`Index Name,Index Date,Open Index Value,High Index Value,Low Index Value,Closing Index Value,Points Change,Change(%),Volume,Turnover (Rs. Cr.),P/E,P/B,Div Yield`
### 2026-11-10 (Tue)
- CM bhavcopy (new UDiFF): HTTP 404, 3809 bytes. 
- sec_bhavdata_full: HTTP 200, 400839 bytes. rows=3552; header=`SYMBOL, SERIES, DATE1, PREV_CLOSE, OPEN_PRICE, HIGH_PRICE, LOW_PRICE, LAST_PRICE, CLOSE_PRICE, AVG_PRICE, TTL_TRD_QNTY, TURNOVER_LACS, NO_OF_TRADES, DELIV_QTY, `
- index close: HTTP 404, 3912 bytes. 
### 2026-11-09 (Mon)
- CM bhavcopy (new UDiFF): HTTP 200, 206935 bytes. rows=3705; header=`TradDt,BizDt,Sgmt,Src,FinInstrmTp,FinInstrmId,ISIN,TckrSymb,SctySrs,XpryDt,FininstrmActlXpryDt,StrkPric,OptnTp,FinInstrmNm,OpnPric,HghPric,LwPric,ClsPric,LastPr`
- sec_bhavdata_full: HTTP 200, 400839 bytes. rows=3552; header=`SYMBOL, SERIES, DATE1, PREV_CLOSE, OPEN_PRICE, HIGH_PRICE, LOW_PRICE, LAST_PRICE, CLOSE_PRICE, AVG_PRICE, TTL_TRD_QNTY, TURNOVER_LACS, NO_OF_TRADES, DELIV_QTY, `
- index close: HTTP 200, 17518 bytes. rows=168; header=`Index Name,Index Date,Open Index Value,High Index Value,Low Index Value,Closing Index Value,Points Change,Change(%),Volume,Turnover (Rs. Cr.),P/E,P/B,Div Yield`
### 2026-11-06 (Fri)
- CM bhavcopy (new UDiFF): HTTP 200, 208064 bytes. rows=3716; header=`TradDt,BizDt,Sgmt,Src,FinInstrmTp,FinInstrmId,ISIN,TckrSymb,SctySrs,XpryDt,FininstrmActlXpryDt,StrkPric,OptnTp,FinInstrmNm,OpnPric,HghPric,LwPric,ClsPric,LastPr`
- sec_bhavdata_full: HTTP 200, 402997 bytes. rows=3560; header=`SYMBOL, SERIES, DATE1, PREV_CLOSE, OPEN_PRICE, HIGH_PRICE, LOW_PRICE, LAST_PRICE, CLOSE_PRICE, AVG_PRICE, TTL_TRD_QNTY, TURNOVER_LACS, NO_OF_TRADES, DELIV_QTY, `
- index close: HTTP 200, 17645 bytes. rows=168; header=`Index Name,Index Date,Open Index Value,High Index Value,Low Index Value,Closing Index Value,Points Change,Change(%),Volume,Turnover (Rs. Cr.),P/E,P/B,Div Yield`
### 2026-11-05 (Thu)
- CM bhavcopy (new UDiFF): HTTP 200, 209545 bytes. rows=3727; header=`TradDt,BizDt,Sgmt,Src,FinInstrmTp,FinInstrmId,ISIN,TckrSymb,SctySrs,XpryDt,FininstrmActlXpryDt,StrkPric,OptnTp,FinInstrmNm,OpnPric,HghPric,LwPric,ClsPric,LastPr`
- sec_bhavdata_full: HTTP 200, 405178 bytes. rows=3568; header=`SYMBOL, SERIES, DATE1, PREV_CLOSE, OPEN_PRICE, HIGH_PRICE, LOW_PRICE, LAST_PRICE, CLOSE_PRICE, AVG_PRICE, TTL_TRD_QNTY, TURNOVER_LACS, NO_OF_TRADES, DELIV_QTY, `
- index close: HTTP 200, 17681 bytes. rows=168; header=`Index Name,Index Date,Open Index Value,High Index Value,Low Index Value,Closing Index Value,Points Change,Change(%),Volume,Turnover (Rs. Cr.),P/E,P/B,Div Yield`
### 2026-11-04 (Wed)
- CM bhavcopy (new UDiFF): HTTP 200, 207731 bytes. rows=3706; header=`TradDt,BizDt,Sgmt,Src,FinInstrmTp,FinInstrmId,ISIN,TckrSymb,SctySrs,XpryDt,FininstrmActlXpryDt,StrkPric,OptnTp,FinInstrmNm,OpnPric,HghPric,LwPric,ClsPric,LastPr`
- sec_bhavdata_full: HTTP 200, 402256 bytes. rows=3554; header=`SYMBOL, SERIES, DATE1, PREV_CLOSE, OPEN_PRICE, HIGH_PRICE, LOW_PRICE, LAST_PRICE, CLOSE_PRICE, AVG_PRICE, TTL_TRD_QNTY, TURNOVER_LACS, NO_OF_TRADES, DELIV_QTY, `
- index close: HTTP 200, 17603 bytes. rows=168; header=`Index Name,Index Date,Open Index Value,High Index Value,Low Index Value,Closing Index Value,Points Change,Change(%),Volume,Turnover (Rs. Cr.),P/E,P/B,Div Yield`

## Yahoo Finance (yfinance)
- yfinance version 1.8.0
- single ticker RELIANCE.NS: 21 rows in 0.5s
- batch of 40 tickers, 5y daily: 40 returned data, 1236 rows, 2.8s
- Nifty 50 index (^NSEI): 21 rows
