import braintree

class BrainTree():
    def __init__(self):
        self.config = braintree.Configuration.configure(braintree.Environment.Sandbox,
                                  merchant_id="kyzs5qxwqpy7jhmh",
                                  public_key="tkzv3g67w4pf7h3m",
                                  private_key="7336eee208ef89df0639aa5a6b2d29d2")
