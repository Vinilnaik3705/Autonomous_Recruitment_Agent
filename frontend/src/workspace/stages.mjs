const next = {screened:['shortlisted','hold'], shortlisted:['interview_scheduled','hold'],
interview_scheduled:['interview_scheduled','interviewed','hold'], interviewed:['feedback_received'],
feedback_received:['selected','rejected','hold'], selected:['offer_sent'],hold:['shortlisted','rejected'],
offer_sent:['onboarding'],onboarding:['complete']};
export function transitions(stage,role){
  return (next[stage] || []).filter(target=>role==='hr'||!['offer_sent','rejected'].includes(target));
}
