---
title: Tools List
date: 2017-09-13 23:09:40
abstract: Something about nanyu
---


{% raw %}
<script>
(function(w, d) {

  function setup(func) {
    var oldonload = w.onload;
    if (typeof w.onload != 'function') {
        w.onload = func;
    } else {
        w.onload = function() {
            oldonload();
            func();
        }
    }
  }
  
  function ip2str(ip) {
    return (ip >>> 24) + "." + ((ip >>> 16)&0xFF) + "." + ((ip >>> 8)&0xFF) + "." + (ip & 0xFF);
  }

  function parseIPv4(ipv4) {
    var ip = 0;
    ipv4.split(".").forEach(function(e){ ip = ip * 256 + parseInt(e);});
    return ip;
  }
  
  function parseCIDR(cidr) {
    var ip      = cidr.substring(0, cidr.indexOf("/"));
    var suffix  = parseInt(cidr.substring(cidr.indexOf("/") + 1));
    var netmask = 0xFFFFFFFF - ((0x1 << (32 - suffix)) - 1);
    var start   = netmask & parseIPv4(ip);
    var end     = start + (0x1 << (32 - suffix)) - 1;
  
    return {
      start: ip2str(start),
      end: ip2str(end),
      netmask: ip2str(netmask)
    }
  }

  setup(function() {
    d.getElementById("ipaddr").onkeyup = function(evt) {
      if (/^[0-9\.]+\/\d+$/.test(evt.target.value)) {
        var ret = parseCIDR(evt.target.value);
        d.getElementById("result").innerHTML = 'Start: ' + ret.start + '<br />' +
        'End: ' + ret.end + '<br />' +
        'Netmask: ' + ret.netmask;
      }
    };
  });

})(window, document);

</script>
{% endraw %}
<a href="fuck">fdasfsfdsafsdfds</a>

<div class="m-input"><input type="text" id="ipaddr" placeholder="Input something" /><label>Input IP address</label><div class="bottom-line"></div></div>

<div id="result"></div>

