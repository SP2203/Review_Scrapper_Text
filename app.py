from flask import Flask, render_template, request, Response
from flask_cors import CORS, cross_origin
from bs4 import BeautifulSoup
from urllib.request import urlopen
import time
import traceback
import pandas as pd
import re

app = Flask(__name__)

df_reviews = pd.DataFrame()


@app.route('/', methods=['GET'])  # route to display the home page
@cross_origin()
def homePage():
    return render_template("index.html")


@app.route('/review', methods=['POST', 'GET'])  # route to show the review comments in a web UI
@cross_origin()
def index():
    if request.method == 'POST':
        try:
            searchString = request.form['content'].replace(" ", "%20")
            flipkart_url = "https://www.flipkart.com/search?q=" + searchString + "&otracker=search&otracker1=search" \
                                                                                 "&marketplace=FLIPKART&as-show=off&as" \
                                                                                 "=off "
            Client = urlopen(flipkart_url)
            flipkartPage = Client.read()
            Client.close()
            time.sleep((4))
            try:
                count = request.form['nos_review'].replace(" ", '')
                count = int(count)
            except:
                count = 5  # By default 5 reviews to be considered

            flipkart_html = BeautifulSoup(flipkartPage, "html.parser")
            box_of_interest = (flipkart_html.find_all("div", {'class': '_1HmYoV _35HD7C'}))[-1]

            product_rows = box_of_interest.findAll("div", {"class": "bhgxx2 col-12-12"})
            for i in range(len(product_rows)):
                products = product_rows[i]
                try:
                    first_product = products.div.div.div.a['href']  # Select the first product in first row
                    break
                except:
                    continue

            productLink = "https://www.flipkart.com" + first_product
            Client = urlopen(productLink)
            prodRes = Client.read()
            Client.close()
            time.sleep(4)

            prod_html = BeautifulSoup(prodRes, "html.parser")  # Load the product HTML page
            product_name = prod_html.find('span', {'class': '_35KyD6'}).text  # Get selected product Name
            product_name = product_name.replace('\xa0', '')

            try:
                # Max reviews for the given product
                max_reviews_present = int(prod_html.find('span', {'class': '_38sUEc'}).span.find_all('span')
                                          [-1].text.split(r' ')[0].split('\xa0')[1].replace(',', ''))
            except:
                return render_template('not_found.html')

            # Get all review HTML page
            rev_tag = prod_html.find('div', {'class': "_1HmYoV _35HD7C col-8-12"}).find('div',
                                                                                        {'class': "_1HmYoV _35HD7C"})
            all_rev = rev_tag.find_all("div", {"class": "bhgxx2 col-12-12"})[-3]

            # If the "All reviews" tag is not present, then read the reviews from there itself

            if not all_rev.find("div", {"class": re.compile('swINJg.*')}):
                print("All review tag not present")
                my_reviews = []
                review_counter = 0

                for tag in (all_rev.find_all('div', {'class': re.compile('_3nrCtb.*')})):

                    try:
                        comment_head = (tag.find('p', {'class': '_2xg6Ul'}).text)
                    except:
                        comment_head = ''

                    try:
                        ratings = (tag.find('div', {'class': 'hGSR34 E_uFuv'}).text)
                    except:
                        ratings = ''

                    try:
                        comment = (tag.find('div', {'class': 'qwjRop'}).text)
                    except:
                        comment = ''

                    try:
                        cust_name = (tag.find('p', {'class': '_3LYOAd _3sxSiS'}).text)
                    except:
                        cust_name = ''

                    review_counter += 1

                    review_dict = {'Index': review_counter, 'Product': product_name,
                                   'CommentHead': comment_head, 'Rating': ratings,
                                   'Comment': comment, "Name": cust_name}
                    my_reviews.append(review_dict)

                global df_reviews
                df_reviews = pd.DataFrame(my_reviews)
                print(my_reviews)
                return render_template('results.html', reviews=my_reviews)

            prefix_url = all_rev.find_all('a')[-1]['href']
            my_reviews = []
            review_counter = 0

            while (len(my_reviews) < count) & (len(my_reviews) < max_reviews_present):

                reviews = "https://www.flipkart.com" + prefix_url
                Client = urlopen(reviews)
                complete_review = Client.read()
                Client.close()

                time.sleep(4)

                review_html = BeautifulSoup(complete_review, 'html.parser')

                reviews_in_page = review_html.find_all('div', {'class': 'col _390CkK _1gY8H-'})

                for review in reviews_in_page:
                    try:
                        comment_head = (review.find('p', {'class': '_2xg6Ul'}).text)
                    except:
                        comment_head = ''

                    try:
                        ratings = (review.find('div', {'class': 'hGSR34 E_uFuv'}).text)
                    except:
                        ratings = ''

                    try:
                        comment = (review.find('div', {'class': 'qwjRop'}).text)
                    except:
                        comment = ''

                    try:
                        cust_name = (review.find('p', {'class': '_3LYOAd _3sxSiS'}).text)
                    except:
                        cust_name = ''

                    review_counter += 1

                    review_dict = {'Index': review_counter, 'Product': product_name, 'CommentHead': comment_head,
                                   'Rating': ratings, 'Comment': comment, "Name": cust_name}
                    if (len(my_reviews) < max_reviews_present) & (len(my_reviews) < count):
                        my_reviews.append(review_dict)
                    else:
                        break

                if review_html.find_all('a', {'class': "_3fVaIS"}):
                    prefix_url = review_html.find_all('a', {'class': "_3fVaIS"})[-1]['href']
                else:
                    break
            #global df_reviews
            df_reviews = pd.DataFrame(my_reviews)

            return render_template('results.html', reviews=my_reviews)
        except Exception as e:
            print('The Exception message is: ', e)
            print(traceback.format_exc())
            return render_template('oops.html')

    else:
        return render_template('index.html')


@app.route('/download', methods=['GET', 'POST'])
@cross_origin()
def download_file():
    return Response(
        df_reviews.to_csv(index=False),
        mimetype="text/csv",
        headers={"Content-disposition":
                     "attachment; filename=Product_Reviews.csv"})


if __name__ == "__main__":
    # app.run(host='127.0.0.1', port=8001, debug=True)
    app.run(debug=False)
