export const getTeamForPick = (round, pick, draftOrder) => {
    const numTeams = draftOrder.length;
    const picksInRound = numTeams;
    const firstPickOfRound = ((round - 1) * picksInRound) + 1;
    const pickIndexInRound = pick - firstPickOfRound;
    
    // For even rounds, reverse the order (snake draft)
    let order = [...draftOrder];
    if (round % 2 === 0) {
      order = order.reverse();
    }
    
    return order[pickIndexInRound];
  };
  
  /**
   * Calculate the current round from a pick number
   */
  export const getRoundFromPick = (pick, numTeams) => {
    return Math.ceil(pick / numTeams);
  };
  
  /**
   * Validate that the team matches the expected team for a pick
   */
  export const validateTeamForPick = (round, pick, teamName, draftOrder) => {
    const expectedTeam = getTeamForPick(round, pick, draftOrder);
    return expectedTeam === teamName;
  };