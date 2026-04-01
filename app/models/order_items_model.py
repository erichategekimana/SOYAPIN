


def main():

    mars_weight = 0.378

    #prompt user for the input

    earth_weight= input('Enter the weight on earth: ')
    earth_weight_fl=float(earth_weight)

    result = earth_weight_fl * mars_weight

    print(f"{earth_weight_fl} on mars is {result}")





if __name__ == '__main__':
    main()