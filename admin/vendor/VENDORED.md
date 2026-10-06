# Vendored front-end assets for the /admin/ content editor

Nothing under /admin/ loads from a CDN. These files were downloaded once from
unpkg.com and committed, so the editor has no third-party runtime dependency
and the site keeps its 'no external hosts' property (the FONT GATE in
verify/check.js checks the public pages; this folder is the only place any
third-party code exists, and it is served from this origin).

  decap-cms@3.16.3  dist/  (entry bundle + 94 lazy chunks + 2 WebAssembly
                            encoders + the empty cms.css + licence text)
  js-yaml@4.1.0     dist/js-yaml.min.js

Every decap-cms file's sha256 was verified against the integrity hash that
unpkg.com publishes for that exact file before it was committed.

| file | bytes | sha256 (base64, from unpkg integrity) |
| --- | --- | --- |
| 103.decap-cms.js | 4628 | W3mLvuZeN8CLVbPbwBuvikkkrZzj8LyiwBbPYuyiRE8= OK |
| 1077.decap-cms.js | 1145 | TW43VXptPCrTzhfJ9BPnpnSzHwu6EckyNwkvBCDMj1g= OK |
| 117.decap-cms.js | 8163 | X0PXt12V1zQ3vRaM3yPdSNWQMFmNce6w0+gg6t9R+Rg= OK |
| 1193.decap-cms.js | 1352 | RZIFF0ho5bewTeA17q2Z0DlpoVvoXnHDbhmM+YjL0BQ= OK |
| 1577.decap-cms.js | 2754 | 41S4uLDsX9x130ABjkHOdypELQbPbk7fEypYpWzhCeI= OK |
| 1957.decap-cms.js | 3958 | Evoe8U3J/D/hA21xL89/AQlwxyFDq55wWP+CfoECUyI= OK |
| 2031.decap-cms.js | 2725 | mhUZKs6ht0T4lQb+B1YIoWbkSKoyOP324Q68s7YaTnA= OK |
| 2035.decap-cms.js | 3523 | RKYLjPu5yg6rGPnumdknknoPZmASlJuY7WJD0ciqcfQ= OK |
| 21.decap-cms.js | 18848 | TDn0+sQBOkDAWcipkx5UxrwkxSg/bLeJWZJl5fBRy5s= OK |
| 2363.decap-cms.js | 2531 | 3HTEQJyXuHjCwfvMIzpmzzk7i/Xn0jZ4qNbk4NsiYS0= OK |
| 2369.decap-cms.js | 4490 | arOLqdmjjyCyfLn7OUeoUlMppHd2U5b1QZP6FcIFk2I= OK |
| 2371.decap-cms.js | 3258 | 73AEtBtjUiZKARlp4GOYrupDsBUyFm/OvoKyTsDrH2E= OK |
| 2533.decap-cms.js | 2178 | pxQO4hANMJqsyhs5skrB3Ww283dkQLidBfN5A0sSOzM= OK |
| 2598.decap-cms.js | 19790 | mygGipKMpLPOxFzKo3sBf5mL/rPozph+MuC9YNW8q+Y= OK |
| 2777.decap-cms.js | 1922 | W6xpyKbeaHnRFNzDOOlQqdXGWc2a/jpyQRIiTH1FeFw= OK |
| 2789.decap-cms.js | 4299 | Lah1e39UxQILjDNcPZOW7EkMBpiPvMocMZJ7703CiSc= OK |
| 2821.decap-cms.js | 4189 | OVVY1apYiD6yxl/Gi7lXHYJk1dPFsENyMw9ikZtVcPc= OK |
| 2953.decap-cms.js | 2245 | ozP3qaGhTdpIeMF5Gen+4N2231uArPXZr1WdWh6ph90= OK |
| 2973.decap-cms.js | 17210 | HwIGtdOiQPMN5xVGIoysRjkn0PaZIOm0B8GcuOPzJpA= OK |
| 3037.decap-cms.js | 2507 | gbjjDBkkZRd+vnUapr53ty8Cla6Nb+mgR+tAvr71Un4= OK |
| 3109.decap-cms.js | 8156 | YJhozQUR/27WIPy+dOlji2JzjljuRKoCieFtEsEUFQY= OK |
| 315.decap-cms.js | 3017 | FNLWvu8KmUnPQ8QzKhZ/ZO0SeuKHMkhNP6c5IWMyjxA= OK |
| 3219.decap-cms.js | 1139 | jgLosSOx2R44ddSQRIl+nQLpRsEgzjAh3T9gBcfMKP8= OK |
| 3763.decap-cms.js | 4334 | Ht8aPE0IKjHHJxmwR+NkFdKUl4047IADOvzVzVlbaYY= OK |
| 3933.decap-cms.js | 9752 | ayWOpjcUKxAW8HRfy4c4ZRYQ7RUYe7NrV+xdk42YvPo= OK |
| 4061.decap-cms.js | 9500 | pyyRDxmbWpecH5qlIftiWlvAtDlr8pSoJak3QJNMCG8= OK |
| 4149.decap-cms.js | 11915 | nBk5Qd4j7NGG71O8ia49Kdo4wRLFqiGlrUm3PewnbJI= OK |
| 4229.decap-cms.js | 7975 | 8LksvNsdxNrQQWdyTpQSZfpmNKCXUp1Nf/MOBbP8rbY= OK |
| 4277.decap-cms.js | 11111 | LM1IdJYwFtx9dOJZh3QMPgmZHmGWiKlBTLIJn4KS7j0= OK |
| 4329.decap-cms.js | 5310 | 8R7/crRxheDx8DCMFVttwBd78wtfEeZrEeDCmEZ4G80= OK |
| 4355.decap-cms.js | 2941 | Tjs7F2EAfAlAm3sMa9zaVtqxmIPV9CHtSDCI55BkLkw= OK |
| 4928.decap-cms.js | 19834 | l/Z/jcvM3ZBXr2E6nuHBaVB73f12V9Mmso6ZXWst/dA= OK |
| 5025.decap-cms.js | 47478 | 7TgVGVhM2/ZmWYhAeA1h0xWZs+jtRzC0xGlpXWA6fdQ= OK |
| 5047.decap-cms.js | 1215 | kf8U/n9hQ45hZHrbnNzO21z60tix3EA2O2dpGc4hvz4= OK |
| 5121.decap-cms.js | 5734 | bRzwkM77FUQ/GN98AWdtYhH80iMlGm+tjfzdHvnZ+LA= OK |
| 533.decap-cms.js | 3074 | 6ftK8svF2UgjmUJVqn1Y4e56GjS6dJu7cOHYhRmaPBw= OK |
| 5409.decap-cms.js | 7488 | k25frVV91amnRbiLn9VPqPgsmOHUO/qGQHBoUA0k4Fc= OK |
| 5415.decap-cms.js | 6025 | u9TG7NSB4r/ej1k3bKWRQss0y2H9C4iDjqL7R4AOQ/M= OK |
| 545.decap-cms.js | 5614 | GLd9g6gMt+FBLtPelTqXSqRImlfEYwM/gsWBnwl6YJI= OK |
| 5749.decap-cms.js | 21152 | PVhekhTkAnxPTmiB0TPkr1VjFG21A3EE0WbFzIjRU7o= OK |
| 5839.decap-cms.js | 6217 | 4oHUZULVUOaD113MRSm6EHXKQ5tABaKHQbxVjTPo9BE= OK |
| 5859.decap-cms.js | 4117 | 7LjSNpm6d3MSRvNI7/VyZIabzcRGJh3cepDZt0qwEhI= OK |
| 5861.decap-cms.js | 10889 | ycIf8BMk+5vD/6zbzHbdV++AgNwb/Flg80/sJ/S4zno= OK |
| 5909.decap-cms.js | 2060 | cjKDTLvku4tyLO1wYfV+hNE1ZCxfQIPg63xZ7ZtUwhc= OK |
| 6069.decap-cms.js | 6128 | kE1YFjKD3KQilwczwoQ+7PkHplcB/nDZ95BLOExq3QM= OK |
| 621.decap-cms.js | 2082 | KOLta/35HcqucuUtWg7p7aeNN1K0sBRqavkxAisUNrY= OK |
| 6261.decap-cms.js | 8672 | CtUWQIqG4lb6EuIK+FXWh60s7RyjmnT0f//9E+LakmU= OK |
| 6329.decap-cms.js | 1972 | vEQ1pVhFCQWNeUy+4UjRFbHWuqEgFGd+WDJgKJpyZfo= OK |
| 6399.decap-cms.js | 15926 | /SZTn5D15YcDlirs3iPrUazx/3r/oQF/oSMQk15FeZA= OK |
| 6411.decap-cms.js | 5059 | Lo4Kcise21d12BHRmumNbMzj4QU+Gyl38AIM751wAes= OK |
| 6549.decap-cms.js | 3725 | jBvsIUxjYnv1FZCM1d+1Cc6AxUuLGKwhX1ArRxUx21s= OK |
| 6683.decap-cms.js | 1208 | 9P27LP7b59lt4eCh5gcIyH0hvh1dGHw92YoZiHNHX6c= OK |
| 6893.decap-cms.js | 921 | S/qlgEFySnrIbY6shZct+WWpGL4IR33P4kzGXhcEvsk= OK |
| 697.decap-cms.js | 3603 | +zdGbh8zIZjrcOmDFnS8B/8nnY0xvG2wKMLc5k8bKLw= OK |
| 7.decap-cms.js | 6839 | hbdlEitH2ohTmsUr9YA8cudxB7g6tSieVXE3TMPSfV8= OK |
| 7045.decap-cms.js | 4985 | 7WtPoccz77WFe8+63xu5nsc2IJh3qHF3fPSBM4nR8Vw= OK |
| 7113.decap-cms.js | 16391 | jSL2yHJGRiJvmD9/1qMYqIXgVJceUf2znfJ2MRwcVcs= OK |
| 7205.decap-cms.js | 4161 | yHatvPGrn5b5ZEEGWqs8UNhHsZkR0huni8US/3V0fG4= OK |
| 7237.decap-cms.js | 2348 | nMNsrb8PWwsqgQyU1j8gA6zh6R3whb4ZIlvTOj8p/PQ= OK |
| 7405.decap-cms.js | 1306 | VB6hTU0WV+Rzr43iHGbT1eDwq+59FOwSib2A//v90N4= OK |
| 7413.decap-cms.js | 27189 | uV4wVPd/h5F+Co9qGIVSGIXaUsK20M/DrhqNgEgwgRI= OK |
| 7477.decap-cms.js | 1257 | f9DET2+SK+Qckha6LjWnU4CYfYR1xzhQNOcWAi8qIso= OK |
| 7589.decap-cms.js | 22408 | SH1AY+ozs3QhMwQQltEP6B687W2Tf4wQbS/SE7ZKIOE= OK |
| 7613.decap-cms.js | 2619 | a7q30t04dqK7+QW94VjpQiDWSkM4WvPDNIERBcaZxW4= OK |
| 7621.decap-cms.js | 777 | 0iodg44pRr6tw3YOriyEeR+uAcxgh7GCf0obRuZ3hgI= OK |
| 7809.decap-cms.js | 14398 | Ee+iQIeBR8BkSyExpDagcILMqSam3pUAviiJ+nl/9W8= OK |
| 7891.decap-cms.js | 6585 | ZEdFou2tSCx1s4egrC1MQVF3/zsyW849PsMMktmtnIM= OK |
| 7957.decap-cms.js | 2739 | S2+hPwbYM6XL/x3wiqaaOl07LSKaNEfdm+B+kpga260= OK |
| 8205.decap-cms.js | 4804 | jsMdYQg50aILExByaXWK/6j509JpHleGMyFh5I3KKkw= OK |
| 8229.decap-cms.js | 7024 | mzMH3QYzMY461Wh83jz+D6uNazCvoUKeZ/s9DkiY2eg= OK |
| 8241.decap-cms.js | 4194 | B0amY37MA0ZyxwsPgkwv1JKwhh/cuYeLGp9/3JE2jv8= OK |
| 8273.decap-cms.js | 3155 | SsOcTWRFdHAjnLDDMX1hLDds8C//9TpGUVSmoU1QBuI= OK |
| 8333.decap-cms.js | 6002 | U60C5VO7YrtBG6CV+2g8KvqTjqxtXfX5nGt4Kpobpc4= OK |
| 8497.decap-cms.js | 520 | I9Wh1gxFWMEkejrlmDA3q1MB/q4Kd1BowVHC+GcdMZg= OK |
| 8573.decap-cms.js | 5311 | 5tPd9CVBAfijYg2EiC2W/EKKEU3XsQFWiAOw6ewV9SE= OK |
| 8677.decap-cms.js | 11670 | RJTCyM6Tuc1loGi2pYs7LvJco+Il980TAwtchKzb5gs= OK |
| 8703.decap-cms.js | 5343 | QH06+ezCB2VVQtEne/MCgOfDA69GPdG2pMX017Q57N0= OK |
| 8973.decap-cms.js | 2882 | eYj1LAxf/i2TmwcmCoD8rv383qiBHTaagSphEBOaDTE= OK |
| 9003.decap-cms.js | 2382 | RJbI1BzCyZ3KOk8zuwSP6cY1b03yIT0WM9Nr2vmMWjw= OK |
| 9049.decap-cms.js | 1782 | StfO3Kf5N14Ky/LlgRMEUsHkoSQED2c0NHl/yTEo9AM= OK |
| 9109.decap-cms.js | 4170 | ACovjB3vQAclLpYLVfatOhhyCFsrlQoP9o8B3iwReDE= OK |
| 9157.decap-cms.js | 963 | 331oii7yzRcpHa4nF+lq8clQuQo8PlQKP8Jy5HtKXfA= OK |
| 9189.decap-cms.js | 6388 | AnMH5yelI+O6TWuTe1JeXqrmGJylnnxSXc5DYnFjiZM= OK |
| 9469.decap-cms.js | 20982 | l6kVSfb1zfFJbHquasAJW3wtk8uhkY1NV9wwO3/j/vE= OK |
| 9493.decap-cms.js | 10592 | GWTJaSbxKgRugwbUsUoENjGc55UbkBt0MhFwm54hcTQ= OK |
| 9571.decap-cms.js | 3260 | 4hZxYdBUTaA3GS3uwe5GzyztRySCzwAbEAFGP9jYsl4= OK |
| 9633.decap-cms.js | 6545 | Q+67HURecccu4WlzEVwnfiKtjyW0YfD/2FQvQ+Y+PaQ= OK |
| 9661.decap-cms.js | 2513 | KT+9OdYNjaD6CwslPpJnnZBqtOEojTbh23Xi3tyKHMA= OK |
| 9691.decap-cms.js | 2125 | xlVuN843wrA+7AsZSGaVPMO9KtqoNFwY0wpSU8J51JY= OK |
| 9711.decap-cms.js | 8064 | jVw9BpHoa29X0fqzEWLWOCn1+EYyU+7i3m6hnC3ZETA= OK |
| 9733.decap-cms.js | 2523 | n9ThP2HnoxuAAvyrAIFAbKusxq6FCkliLwgC/a6+c3c= OK |
| 977.decap-cms.js | 37025 | Sq2kycwSVdQ/YeM+4NlJm5a8qbbYhqadvhwvpzmZHgs= OK |
| 9829.decap-cms.js | 4380 | 3XBwX9J0ZSSbMHrET1DuxskIDcXihqrPstJdWXAtdvg= OK |
| 997.decap-cms.js | 17479 | hs66rZkPtDTUHTOoC1mEitU6IQF50MPYtEfYZpqmpWs= OK |
| cms.css | 277 | WyyTNnb4jCiu+l25rkgpgL7YVS3AeJlnDJ1WR1EuU3E= OK |
| cms.js.LICENSE.txt | 8144 | xs4RXbAdojQoJlLKFiuW9xUH2smrheaZSk6zrtMVV3k= OK |
| dd5d52671a5763720504.wasm | 281261 | tghbtnAvFE6dxgFtWNIws0qEl2vw0IC3OQtLSxN9arc= OK |
| decap-cms.js | 5167389 | fB79a2FrR4biea7vGU3SFkmnIFjTvI0feJAbV0YQ37g= OK |
| decap-cms.js.LICENSE.txt | 8144 | xs4RXbAdojQoJlLKFiuW9xUH2smrheaZSk6zrtMVV3k= OK |
| f728dc876b39e5273411.wasm | 345584 | OcJ5Jp7BFjuYe21pdJRY49WwO5WF9YtspUVbdrUEowU= OK |
| js-yaml.min.js | 39430 | Rdw90D3AegZwWiwpibjH9wkBPwS9U4bjJ51ORH8H69c= (js-yaml, downloaded directly; sha256 above) |
