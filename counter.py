import numpy as np
import cv2
import requests
import time

def center(x, y, w, h):
    x1 = int(w / 2)
    y1 = int(h / 2)
    cx = x + x1
    cy = y + y1
    return cx,cy

# URL da Aplicação em Flask na Nuvem
url_flask = 'https://k1y4.pythonanywhere.com/receber_dados'

# Definindo o intervalo de tempo (segundos) desejado ao enviar para a Nuvem
intervalo_envio = 20

# Obtendo o tempo atual
ultimo_envio = time.time()

# Fonte de Captura de Vídeo
cap = cv2.VideoCapture('http://192.168.0.29:8000/stream.mjpg')

fgbg = cv2.createBackgroundSubtractorMOG2()

detects = []

posL = 150
offset = 30

xy1 = (20, posL)
xy2 = (300, posL)


total = 0

up = 0
down = 0

while 1:
    ret, frame = cap.read()

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    #cv2.imshow("gray", gray)

    fgmask = fgbg.apply(gray)
    #cv2.imshow("fgmask", fgmask)

    retval, th = cv2.threshold(fgmask, 200, 255, cv2.THRESH_BINARY)
    #cv2.imshow("th", th)

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))

    opening = cv2.morphologyEx(th, cv2.MORPH_OPEN, kernel, iterations = 2)
    #cv2.imshow("opening", opening)

    dilation = cv2.dilate(opening,kernel,iterations = 8)
    #cv2.imshow("dilation", dilation)

    closing = cv2.morphologyEx(dilation, cv2.MORPH_CLOSE, kernel, iterations = 8)
    cv2.imshow("closing", closing)

    cv2.line(frame,xy1,xy2,(255,0,0),3)

    cv2.line(frame,(xy1[0],posL-offset),(xy2[0],posL-offset),(255,255,0),2)

    cv2.line(frame,(xy1[0],posL+offset),(xy2[0],posL+offset),(255,255,0),2)

    contours, hierarchy = cv2.findContours(dilation,cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)
    i = 0
    for cnt in contours:
        (x,y,w,h) = cv2.boundingRect(cnt)

        area = cv2.contourArea(cnt)
        
        if int(area) > 3000 :
            centro = center(x, y, w, h)

            cv2.putText(frame, str(i), (x+5, y+15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255),2)
            cv2.circle(frame, centro, 4, (0, 0,255), -1)
            cv2.rectangle(frame,(x,y),(x+w,y+h),(0,255,0),2)
            if len(detects) <= i:
                detects.append([])
            if centro[1]> posL-offset and centro[1] < posL+offset:
                detects[i].append(centro)
            else:
                detects[i].clear()
            i += 1

    if i == 0:
        detects.clear()

    i = 0

    if len(contours) == 0:
        detects.clear()

    else:

        for detect in detects:
            for (c,l) in enumerate(detect):


                if detect[c-1][1] < posL and l[1] > posL :
                    detect.clear()
                    up+=1
                    total-=1
                    cv2.line(frame,xy1,xy2,(0,255,0),5)
                    continue

                if detect[c-1][1] > posL and l[1] < posL:
                    detect.clear()
                    down+=1
                    total+=1
                    cv2.line(frame,xy1,xy2,(0,0,255),5)
                    continue

                if c > 0:
                    cv2.line(frame,detect[c-1],l,(0,0,255),1)

    cv2.putText(frame, "LOTACAO ATUAL: "+str(total), (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255),2)
    cv2.putText(frame, "SUBINDO: "+str(up), (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0),2)
    cv2.putText(frame, "DESCENDO: "+str(down), (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255),2)
    
    cv2.imshow("frame", frame)
    
    tempo_atual = time.time()

    # Verificar se o tempo de envio passou do intervalo desejado
    if tempo_atual - ultimo_envio >= intervalo_envio:
        # Crie um dicionário com os dados a serem enviados
        data = {
            'timestamp': tempo_atual,
            'contador': total
        }

        # Faça uma requisição HTTP POST para enviar os dados
        response = requests.post(url_flask, json=data)

        # Verificando a resposta
        if response.status_code == 200:
            print('Dados enviados com sucesso para a Nuvem!')
        else:
            print('Erro ao enviar os dados para a Nuvem!')

        # Atualize o tempo do último envio
        ultimo_envio = tempo_atual

    
    if cv2.waitKey(30) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
