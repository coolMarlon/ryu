for i in $(seq 1 4);
    do
    let port=i+6660
    xterm -title "app$i" -hold -e ryu-manager ryu.openexchange.network.shortest_forwarding --ofp-tcp-listen-port=$port --oxp-role=domain --oxp-domain-id=$i --oxp-server-ip=10.103.90.127 --oxp-server-port=6688 --observe-links --oxp-period=2 --oxp-flags=8 &
    done


