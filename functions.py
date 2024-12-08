def identify_card_type(card):
    if card[0]==5:
        return "Mastercard"
    else:
        return "Visa"
    
def check_credentials(selected_card, transfer_sum, cvv, pin):
    if selected_card.amount >= transfer_sum and selected_card.cvv==cvv and selected_card.pin==pin:
        return True
    else:
        return False