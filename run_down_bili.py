
""" from search_client import HashSearchClient
from frame_box import FrameBox
frame_box = FrameBox()
search_client = HashSearchClient() """
from download_bilibili import main
""" main.update("26291", {
    "cid": 70676055,
    "bvid": "bv2233",
    "epid": 259653
}, 6035)

search_client.add_hash([
    '2354235', 
    '2542345'
])

results = search_client.search_hash("a52434b4dc7ae689")
print(results)
results = frame_box.search_hash(results)
print(results)
results = frame_box.search_cid(results)
print(results) """
main.main()

