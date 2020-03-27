package main

import (
	"fmt"
	"github.com/gorilla/websocket"
	"log"
	"net/http"
)

type Client struct {
	conn *websocket.Conn
}

func serveWs(w http.ResponseWriter, r *http.Request) {
	fmt.Print("hello ws")
	upgrader := websocket.Upgrader{ReadBufferSize:  1024, WriteBufferSize: 1024,}
	c, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		log.Println(err)
		return
	}
	defer c.Close()

	for {
		mt, msg, err := c.ReadMessage()
		if err != nil {
			log.Println("write: ", err)
			break
		}
		log.Printf("message type %d", mt)
		log.Printf("recv: %s", msg)
	}

}

func main() {
	http.HandleFunc("/echo", serveWs)

	err := http.ListenAndServe("0.0.0.0:8080", nil)
	if err != nil {
		log.Fatal("ListenAndServe: ", err)
	}
}
