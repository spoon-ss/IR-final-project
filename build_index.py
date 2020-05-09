from flaskapp.index import buildIndex
import time
if __name__ == "__main__":

    start_time = time.time()
    buildIndex("flaskapp/index/covid_comm_full_text.json", 100)
    print("=== Built index in %s seconds ===" % (time.time() - start_time))
