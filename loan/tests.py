from django.test import TestCase

# Create your tests here.

import math

def get_weekly_interest(annual_interest):
    return math.pow(1+annual_interest, 1/(365/7)) - 1

if __name__ == '__main__':
    print(get_weekly_interest(0.14))
    print(help(TestCase))
