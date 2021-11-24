# -*- coding: utf-8 -*-
"""
Created on Thu Jun 25 04:23:23 2020

@author: Vinicius
"""
#%% IMPORTAR PACOTES
import requests as rq 
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
import codecs
import smtplib
from datetime import datetime as dt
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
#%% EXTRAIR DADOS
url = 'https://www.fundamentus.com.br/resultado.php'
headers = {'user-agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.61 Safari/537.36'}
page = rq.get(url, headers=headers)
soup = BeautifulSoup(page.text, 'html.parser')
html_table = soup.find_all('table', id='resultado')
#CRIAR O DATAFRAME BRUTO
df = pd.read_html(str(html_table), thousands='.', decimal=',')[0]
#%% FORMATAR DADOS
pd.set_option('max_columns', None)
#RENOMEAR COLUNAS PARA MELHOR MANIPULAÇÃO
df.columns = ['codigo','preco','p_l','p_vp','psr','dy','p_ativo','p_cap_giro',
'p_ebit','p_ativ_circ_liq','ev_ebit','ev_ebitda','mrg_ebit','mrg_liq','liq_corr','roic',
'roe','liq_2m','pl','div_brut_patrim','cresc_rec_5a']

#FUNÇÃO PARA CONVERTER AS COLUNAS QUE CONTÊM STRINGS DE PERCENTUAIS EM VALORES DECIMAIS
def convert_perc(dataframe, *args):
    for col in args:
        try:
            dataframe[str(col)+'_nf'] = dataframe[col].str.rstrip('%').str.replace('.','').str.replace(',','.').astype(float)/100
        except:
            continue
   
#FUNÇÃO PARA FORMATAR PARA R$
def formata_rs(x):
    return 'R$ {:,.2f}'.format(x).replace(',','X').replace('.',',').replace('X','.')
     
convert_perc(df,'dy','mrg_ebit','mrg_liq', 'roic','roe','cresc_rec_5a')

#%% REDUÇÃO DO NÚMERO DE ATIVOS
#EXCLUSÃO DE AÇÕES NÃO NEGOCIADAS NOS ÚLTIMOS 2 MESES
df = df.query('liq_2m > 0')
print(len(df))
#APÓS ESSA EXCLUSÃO, SELEÇÃO DE APENAS AS 70% MAIS NEGOCIADAS NOS ÚLTIMOS 2 MESES
df = df.query('liq_2m > liq_2m.quantile(0.3)')
print(len(df))
#%% ESTRATÉGIAS
dividendos = df.query('dy_nf > 0.05 & cresc_rec_5a_nf > 0 & liq_corr > 1 & mrg_ebit_nf > 0 & mrg_liq_nf > 0').sort_values(by=['dy_nf'], ascending=False)
preco_at_circ_liq = df.query('p_ativ_circ_liq > 0.5 & p_ativ_circ_liq < 1.1 & cresc_rec_5a_nf > 0 & liq_corr > 1 & (roic_nf > 0.05 | roe_nf >0.05)').sort_values(by=['p_ativ_circ_liq'])
preco_vp_lucrativas = df.query('p_vp > 0.7 & p_vp < 1 & cresc_rec_5a_nf > 0 & mrg_ebit_nf > 0 & mrg_liq_nf > 0 & (roic_nf > 0.1 | roe_nf > 0.15)').sort_values(by=['p_vp'])
alta_liq_bx_endiv = df.query('liq_corr > 1 & div_brut_patrim > 0 & div_brut_patrim < 1 & p_ativ_circ_liq > 0 & cresc_rec_5a_nf > 0 & mrg_ebit_nf > 0 & mrg_liq_nf > 0 & (roic_nf > 0.1 | roe_nf > 0.15)').sort_values(by=['p_ativ_circ_liq'])
#%% FORMATACAO DOS RESULTADOS
def formata_exib_final(*args):
    for df in args:
        try:
            df['liq_2m'] = df['liq_2m'].apply(lambda x: '{:,.0f}'.format(x)).str.replace(',','.')
            df['preco'] = df['preco'].apply(formata_rs)
            df['pl'] = df['pl'].apply(formata_rs)
            df.drop(['dy_nf','mrg_ebit_nf','mrg_liq_nf','cresc_rec_5a_nf','roe_nf','roic_nf'], axis=1, inplace=True)
            df.columns = ['Código', 'Preço', 'P/L', 'P/VP', 'PSR', 'Div. Yield', 'P/Ativo', 'P/Cap.Giro', 'P/EBIT', 
                          'P/Ativ.Circ.Liq', 'EV/EBIT', 'EV/EBITDA', 'Marg.EBIT', 'Marg.Liq', 'Liq.Corr', 'ROIC', 'ROE',
                          'Liquidez Ult. 2 Meses(R$)', 'Patr. Líquido', 'Div.Bruta/PL', 'Cresc.Rec.(5 anos)']
            # return df
        except:
            continue
formata_exib_final(dividendos, preco_at_circ_liq, preco_vp_lucrativas, alta_liq_bx_endiv)
#%%MONTAR HTMLS DAS TABELAS
divhtml = '<p class="criterios">Não foram encontradas ações com o critério especificado.</p>' if dividendos.empty else dividendos.to_html(index=False, classes='tdividendos')
paclhtml = '<p class="criterios">Não foram encontradas ações com o critério especificado.</p>' if preco_at_circ_liq.empty else preco_at_circ_liq.to_html(index=False, classes='tpacl')
pvpluchtml = '<p class="criterios">Não foram encontradas ações com o critério especificado.</p>' if preco_vp_lucrativas.empty else preco_vp_lucrativas.to_html(index=False, classes='tpvpluc')
liqbxendivhtml = '<p class="criterios">Não foram encontradas ações com o critério especificado.</p>' if alta_liq_bx_endiv.empty else alta_liq_bx_endiv.to_html(index=False, classes='tliqbxendiv')    
#%% ABRIR ARQUIVO EXTERNO E MONTAR O HTML FINAL
f = codecs.open('C:/path/email_template.html','r',encoding='utf-8')
template = f.read()
f.close()
hoje = dt.now()
data_hoje = str(hoje.day) + '/' + str(hoje.month) + '/' + str(hoje.year)
html_final = template.replace('$dividendos$',divhtml).replace('$pacl$',paclhtml).replace('$pvpluc$',pvpluchtml).replace('$liqbxendiv$',liqbxendivhtml).replace('$XX/XX/XXXX$', data_hoje)
#%% ENVIO DE EMAIL COM OS ALERTAS
fromaddr = "sender@isp.com"
toaddr = ["dest1@isp.com","dest2@isp.com"]
msg = MIMEMultipart()
msg['From'] = "Analise Fundamentalista"
msg['To'] = ", ".join(toaddr)
msg['Subject'] = "Analise Fundamentalista - " + data_hoje

body = html_final
msg.attach(MIMEText(body, 'html'))
# 
server = smtplib.SMTP('smtp.isp.com', 587)
server.starttls()
server.login(fromaddr, "password")
text = msg.as_string()
server.sendmail(fromaddr, toaddr, text)
server.quit()
