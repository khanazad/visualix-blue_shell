package main

import (
	"crypto/tls"
	"github.com/gorilla/websocket"
	"log"
	"net/http"
	"net/url"
	"time"
)

var addr = "localhost:8443"

// This is only for test purposes, in general, clients should only accept signed certificates
func enableSelfSignedCerts() {
	http.DefaultTransport.(*http.Transport).TLSClientConfig = &tls.Config{InsecureSkipVerify: true}
	websocket.DefaultDialer.TLSClientConfig = &tls.Config{InsecureSkipVerify: true}
}

func main() {
	enableSelfSignedCerts()
	u := url.URL{Scheme:"wss", Host: addr, Path: "/echo"}
	log.Printf("connecting to %s", u.String())

	c, _, err := websocket.DefaultDialer.Dial(u.String(), nil)
	if err != nil {
		log.Fatal("dial:", err)
	}
	defer c.Close()

	ticker := time.NewTicker(time.Second)
	defer ticker.Stop()

	for {
		select {
		case t := <- ticker.C:
			err := c.WriteMessage(websocket.TextMessage, []byte(t.String()))
			if err != nil {
				log.Println("write: ", err)
				return
			}
		}

	}
	
}
