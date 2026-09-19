ENERGY_JOURNEY = {
    "name": "Energy Plan Recovery",
    "sections": [
        {
            "id": "customer_identity",
            "fields": ["customer_name"],
            "script": "Could you please confirm your full name?"
        },
        {
            "id": "property",
            "fields": ["property_type"],
            "script": "Is this for a house, an apartment, a commercial property, or another type of property?"
        },
        {
            "id": "usage",
            "fields": ["monthly_bill", "monthly_usage"],
            "script": "Approximately how much do you normally pay for electricity each month?"
        },
        {
            "id": "plan",
            "fields": ["plan_interest"],
            "script": "Are you interested in comparing energy plans?"
        },
        {
            "id": "callback",
            "fields": ["callback_preference"],
            "script": "If we need a human follow-up, is there a preferred time to contact you?"
        }
    ],
    "required_fields": [
        "customer_name",
        "property_type",
        "monthly_bill",
        "plan_interest"
    ],
    "opening_script": (
        "Hello, this is the energy support team. "
        "You recently started comparing energy options but did not complete the process. "
        "I can help finish it with you. Is now a good time?"
    ),
    "completion_script": (
        "Thank you. I have captured the information needed "
        "to complete your energy journey."
    )
}
